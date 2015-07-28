
from toddler.managers import RabbitManager, json_task, RequeueMessage
from .managers import crawlmanager
import requests
from requests import exceptions
import addict
import ujson
import toddler
from datetime import datetime, timezone, timedelta
import dateutil.parser
from threading import Event
from concurrent.futures import Future
from .redis import RedisListener, RedisPublisher
import time


class ChangeQueue(Exception):
    def __init__(self, host, *args, **kwargs):
        self.host = host
        super(ChangeQueue, self).__init__(*args, **kwargs)


class CrawlerRedisListener(RedisListener):

    def __init__(self, *args, **kwargs):

        super(CrawlerRedisListener, self).__init__(*args, **kwargs)

        self._currently_crawled_hosts = {}
        self._last_crawl_times = {}
        self.hosts = []

    def host_is_being_crawled(self, url, host=None):

        if host is None:
            host = crawlmanager.extract_hostname(url)
        try:
            return self._currently_crawled_hosts[host] > 0
        except KeyError:
            return False

    def host_last_crawl_time(self, url, host=None):
        if host is None:
            host = crawlmanager.extract_hostname(url)

        try:
            return self._last_crawl_times[host]
        except KeyError:
            return datetime(1971, 1, 1, 0, 0, 0, 0, timezone.utc)

    def on_connect(self, connection):

        self.hosts = [x.decode('utf8') for x in connection.smembers('hosts')]

    def work(self, item):

        data = item['data'].decode("utf8")
        if item['channel'] == b"hosts:add":
            self.hosts.append(data)
        else:
            time, url = data.split("\0")
            time = dateutil.parser.parse(time)
            host = crawlmanager.extract_hostname(url)
            if item['channel'] == b"crawl:start":
                try:
                    self._currently_crawled_hosts[host] += 1
                except KeyError:
                    self._currently_crawled_hosts[host] = 1

            elif item['channel'] == b"crawl:stop":
                self._last_crawl_times[host] = time
                try:
                    self._currently_crawled_hosts[host] -= 1
                    if self._currently_crawled_hosts[host] == 0:
                        del self._currently_crawled_hosts[host]
                except KeyError:
                    pass


class CrawlerRedisPublisher(RedisPublisher):

    def _send_url_to_channel(self, channel, url):
        message = "\0".join((datetime.now(timezone.utc).isoformat(), url))
        self.publish(channel, message)

    def send_start_crawl(self, url):
        self._send_url_to_channel('crawl:start', url)

    def send_end_crawl(self, url):
        self._send_url_to_channel('crawl:stop', url)


class Crawler(RabbitManager):

    def __init__(self, redis_url="localhost", **kwargs):

        self._redis_url = redis_url
        self._crawl_throttle = 2  # seconds
        # auto queue, the parent don't know what to do with it
        # but it won't raise errors
        kwargs["queue"] = "auto"

        super(Crawler, self).__init__(**kwargs)

        self.listener_promise = Future()

        self.listener_promise.add_done_callback(self.listener_is_done)

        self.listener = CrawlerRedisListener(self._redis_url,
                                             ['crawl:start', 'crawl:stop',
                                              'hosts:add'],
                                             self.log, self.listener_promise)
        self.stopped = False

        self.publisher = CrawlerRedisPublisher(redis_url)
        self.running = Event()
        self.running.set()

        self._last_queue_host = None

    def listener_is_done(self, promise):

        if promise.cancelled():
            # smth went wrong, shutdown crawler
            self.log.warning("Shutting down, lost contact with crawl listener")
            self.stop()
        else:
            # listener is stopped, are we stopping too? if not restart it
            if not self.stopped:
                self.listener.start()

    def stop(self):

        self.stopped = True
        super(Crawler, self).stop()

    def __enter__(self):

        super(Crawler, self).__enter__()
        self.listener.start()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):

        self.listener.stop()

        super(Crawler, self).__exit__(exc_type, exc_val, exc_tb)

    def should_i_crawl(self, url):

        host = crawlmanager.extract_hostname(url)

        if self.listener.host_is_being_crawled(url, host=host):
            return False
        elif (self.listener.host_last_crawl_time(url, host=host)
                + timedelta(seconds=self._crawl_throttle) <=
                datetime.now(timezone.utc)):
                return True
        else:
            return False

    def send_result(self, req, crawl_request):

        result = addict.Dict()

        result.body = req.text
        result.cookies = [(key, val)
                          for key, val in req.cookies.get_dict().items()]
        result.url = crawl_request.url
        result.crawl_task = crawl_request
        result.actions = crawl_request.actions
        result.headers = req.headers
        result.status_code = req.status_code
        result.crawl_time = datetime.now(timezone.utc).isoformat()
        toddler.send_message_sync(
            self._rabbitmq_url,  # this is the rabbit url
            ujson.dumps(result.to_dict()),
            exchange=self._exchange,
            routing_key=self._routing_key
        )

    def send_empty_result(self, crawl_request, e):
        result = addict.Dict()
        result.body = str(e)
        result.status_code = 500
        result.url = crawl_request.url
        result.crawl_task = crawl_request
        result.actions = crawl_request.actions
        result.crawal_time = datetime.now(timezone.utc).isoformat()
        toddler.send_message_sync(
            self._rabbitmq_url,
            ujson.dumps(result.to_dict()),
            exchange=self._exchange,
            routing_key=self._routing_key
        )

    def another_queue(self, old_host):

        make_queue_name = lambda x: "CrawlRequest:{}".format(x)

        host_index = self.listener.hosts.index(old_host)
        if host_index+1 == len(self.listener.hosts):
            return make_queue_name(self.listener.hosts[0])
        else:
            return make_queue_name(self.listener.hosts[1])

    def on_message(self, channel, basic_deliver, properties, body):
        """Invoked when message received from rabbit

        :param pika.channel.Channel channel:
        :param pika.spec.Basic.Deliver basic_deliver:
        :param pika.spec.BasicProperties properties:
        :param str body:
        :return:
        """

        self.log.info("Received messages # %s from %s",
                      basic_deliver.delivery_tag,
                      properties.app_id)

        try:
            if self._tasks_number >= self._max_tasks:
                raise RuntimeError("Max tasks limit reached")

            self._tasks_number += 1

            ftr = self._executor.submit(self.process_task, body)

            def process_done(future: Future):
                nonlocal self
                self._tasks_number -= 1
                if future.cancelled():
                    # process_task ended by cancel
                    self.requeue_message(self.requeue_message(
                        basic_deliver.delivery_tag)
                    )
                else:
                    if future.exception():
                        exception = future.exception()
                        if (not isinstance(exception, RequeueMessage)
                                and not isinstance(exception, ChangeQueue)):
                            self.log.exception(exception)

                        self.requeue_message(
                            basic_deliver.delivery_tag
                        )
                        if isinstance(exception, ChangeQueue):
                            if not self.running.is_set():
                                self.running.clear()
                                self.log.info("Changing queues")
                                self.stop_consuming()
                                self._queue = self.another_queue(
                                    exception.host)
                                self.running.set()
                    else:
                        self.acknowledge_message(basic_deliver.delivery_tag)

            ftr.add_done_callback(process_done)

            return ftr

        except RuntimeError:
            self.requeue_message(basic_deliver.delivery_tag)
            time.sleep(0.5)

        except Exception as e:
            self.log.exception(e)
            self.requeue_message(basic_deliver.delivery_tag)
            time.sleep(10)

    def run(self):
        """Run consumer"""

        self.log.info("Running consumer")
        connection = self.connect()
        """:type: pika.SelectConnection"""

        channel = connection.channel()
        self._channel = channel
        self._connection = connection

        while not self.stopped:
            self.running.wait(5)
            if self.stopped:
                break

            for method_frame, properties, body in channel.consume(self.queue):
                while self._tasks_number >= self._max_tasks:
                    time.sleep(0.1)

                self.on_message(channel, method_frame, properties, body)
            time.sleep(0.1)

    @property
    def queue(self):

        if self._last_queue_host is None:
            host_index = 0
        else:
            host_index = self.listener.hosts.index(self._last_queue_host)
            if host_index >= len(self.listener.hosts):
                host_index = 0

        host = self.listener.hosts[host_index]
        self._last_queue_host = host
        return "CrawlRequestQueue_{}".format(host)

    def download_content(self, crawl_request):

        s = requests.Session()

        if len(crawl_request.cookies) > 0:
            [s.cookies.set(name, value)
             for name, value in crawl_request.cookies]
        try:
            if isinstance(crawl_request.referer, str):
                s.headers.update({'referer': crawl_request.referer})
        except KeyError:
            pass

        try:
            method = str(crawl_request.method).upper()
        except KeyError:
            method = "GET"
        response = None
        try:
            if method == "POST":
                try:
                    response = s.post(str(crawl_request.url),
                                 data=crawl_request.data)
                except KeyError:
                    try:
                        response = s.post(str(crawl_request.url),
                                     json=crawl_request.json)
                    except KeyError:
                        response = s.post(str(crawl_request.url))
            else:
                response = s.get(str(crawl_request.url))
        except TypeError as e:
            self.log.error("Got TypeError on url" + repr(crawl_request))
            raise e
        except (exceptions.ConnectionError, exceptions.RequestException) as e:
            self.log.warning(
                "Connection error with {}: {}".format(crawl_request.url,
                                                      str(e)))
            self.send_empty_result(crawl_request, e)
        except Exception as e:
            self.log.error("Exception on {} ".format(crawl_request.url))
            self.log.error(repr(crawl_request))
            self.log.exception(e)

        return method, response

    @json_task
    def process_task(self, crawl_request):
        """
        Processes the task

        `We are in thread, no asyncio please, as we do not attach event loop
         here`

        :param crawl_request:
        :return:
        """

        crawl_request = addict.Dict(crawl_request)
        wait_counter = 0
        while not self.should_i_crawl(crawl_request.url):
            # self.log.debug("It's not the time to crawl {}".format(
            #     crawl_request.url))
            e = Event()
            e.wait(0.01)
            wait_counter += 1

            if self.stopped or wait_counter > 5:
                # @TODO add get host

                raise ChangeQueue(crawlmanager.extract_hostname(
                    crawl_request.url
                ))

        self.log.debug("Will crawl: {}".format(crawl_request.url))
        self.publisher.send_start_crawl(crawl_request.url)
        try:
            if "timeout" not in crawl_request:
                raise KeyError

            timeout = dateutil.parser.parse(crawl_request.timeout)
            if timeout.tzinfo is None:
                timeout = timeout.replace(tzinfo=timezone.utc)

            if datetime.now(timezone.utc) <= timeout:
                raise RequeueMessage
        except (KeyError, ValueError, TypeError):
            # no timeout so do it asap
            pass

        method, response = self.download_content(crawl_request)

        self.publisher.send_end_crawl(crawl_request.url)

        if response is None:
            raise RequeueMessage

        self.log.info("{} - {} {}".format(method, response.status_code,
                                          crawl_request.url))
        self.send_result(response, crawl_request)
