__author__ = 'michal'

from . import RabbitManager, RequeueMessage
from ..redis import RedisPublisher
from . import json_task
from addict import Dict
from urllib import parse, robotparser
from bs4 import BeautifulSoup
import functools
import toddler
from toddler import send_message_sync
import ujson
import datetime
from datetime import timedelta
import base64
from toddler.models import Host, RobotsTxt, upsert_crawl_document,\
    connect as mongo_connect, CrawlDocument, hash_url
import re
from ..rabbit_sender import declare_queue


def match_url_patterns(url, config_patterns):
    """
    Matches url against config:
    :param url:
    :param config:
    :return list:
    """

    def _match_pattern(config_pattern):
        for pattern in config_pattern['patterns']:
            if re.match(pattern, url):
                return list(config_pattern['actions'])
                # mongoengine returns as BaseList and it causes problems
                # for addict
        return None

    return_actions = []

    for patterns in config_patterns:
        actions = _match_pattern(patterns)
        if actions is not None:
            return_actions = actions

    return return_actions


def now():
    return datetime.datetime.now(datetime.timezone.utc)


class NoRobotsForHostError(Exception):
    pass


class HostLocked(Exception):

    def __init__(self, message, block_date: datetime.datetime,
                 *args, **kwargs):
        self.block_date = block_date
        super(HostLocked, self).__init__(message, *args, **kwargs)


class HostLock(object):

    def __init__(self, hostname):
        self.host = Host.objects(host=hostname).first()

    def lock(self):
        self.host.block = True
        self.host.block_date = datetime.datetime.now(datetime.timezone.utc)
        self.host.save()

    def unlock(self):
        self.host.block = False
        self.host.save()

    def __enter__(self):
        if self.host.block:
            block_date = self.host.block_date
            if block_date.tzinfo is None:
                block_date = block_date.replace(tzinfo=datetime.timezone.utc)

            if block_date + timedelta(hours=1) >= datetime.datetime.now(
                    datetime.timezone.utc):
                raise HostLocked(self.host.host, self.host.block_date)

        self.lock()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.unlock()

@functools.lru_cache(1024)
def can_fetch_url(robots_url, robots_content, url, user_agent):

    rparser = robotparser.RobotFileParser(robots_url)
    rparser.parse(robots_content.splitlines())

    return rparser.can_fetch(user_agent, url)


@functools.lru_cache(2048)
def can_index_html(html, actions):

    if "noindex" in actions:
        return False

    soup = BeautifulSoup(html)

    def get_robots_content(prev, tag):
        try:
            if tag['name'].lower() == "robots":
                return " ".join((prev, tag['content'].lower()))
            else:
                raise KeyError
        except KeyError:
            return prev
    metas = soup.find_all("meta")
    if metas is not None:
        if "noindex" in functools.reduce(get_robots_content,
                                         metas, ""):
            return False

    return True


@functools.lru_cache(2048)
def extract_hostname(url):
    parsed_result_url = parse.urlparse(url)
    return parsed_result_url.hostname


def has_robots_txt(host: Host):

    if host.ignore_robots:
        return True

    if host.robots_txt.status == 'none':
        return False

    if host.robots_txt.status == 'waiting':
        raise RequeueMessage

    if host.robots_txt.expires is not None:
        robots_expiry = host.robots_txt.expires.replace(
            tzinfo=datetime.timezone.utc)
        if now() > robots_expiry:
            return False
    return True


def retrieve_links(result_url, soup: BeautifulSoup):

    parsed_result_url = parse.urlparse(result_url)

    def _fix_url(url):

        parsed_url = parse.urlparse(url)
        if parsed_url.hostname is None:
            return (parsed_result_url.scheme + "://"
                    + parsed_result_url.hostname + url)
        else:
            return url

    accepted_rels = ['alternate', 'first', 'last',
                             'next', 'prev', 'up']

    for tag in soup.select("a"):
        try:
            for rel in tag['rel']:
                if rel in accepted_rels:
                    yield _fix_url(tag['href'])
                    break
        except KeyError:
            if tag.name == "a":
                try:
                    if not tag['href'].startswith("#"):
                        yield _fix_url(tag['href'])
                except KeyError:
                    pass


class CrawlHostPublisher(RedisPublisher):

    def add_host(self, host_name: str):
        if not self.is_host_on_list(host_name):
            self.redis.sadd('hosts', host_name)
            self.redis.publish('hosts:add', '{}'.format(host_name))

    def is_host_on_list(self, host_name):
        return self.redis.sismember('hosts', host_name)



class CrawlManager(RabbitManager):

    def __init__(self, mongo_url, *args, **kwargs):

        self._mongo_url = mongo_url
        """:type: pymongo.MongoClient"""

        if 'user_agent' in kwargs:
            self._user_agent = kwargs['user_agent']
        else:
            self._user_agent = "Toddler/" + toddler.__version__

        self._connect_mongo()
        try:
            self._crawl_request_delay = kwargs['crawl_request_delay']
        except KeyError:
            self._crawl_request_delay = 5

        if 'redis_url' in kwargs:
            self._redis_url = kwargs['redis_url']
            del kwargs['redis_url']

        super(CrawlManager, self).__init__(*args, **kwargs)

        self.publisher = CrawlHostPublisher(self._redis_url)

    def _connect_mongo(self):
        mongo_connect(host=self._mongo_url)

    def send_message(self, msg, exchange):

        return send_message_sync(
            self._rabbitmq_url,
            ujson.dumps(msg),
            exchange,
            exchange
        )

    def get_host(self, hostname):

        return Host.objects(host=hostname).first()

    def get_host_by_result(self, crawl_result: Dict):
        return self.get_host(extract_hostname(crawl_result.url))

    def extract_requests(self, crawl_result):
        """
        Generates crawl requests out of crawl result.
        :param crawl_result:
        :return:
        """
        crawl_result = Dict(crawl_result)

        if "nofollow" in crawl_result.actions:
            raise StopIteration

        host = self.get_host_by_result(crawl_result)
        if not has_robots_txt(host):
            raise NoRobotsForHostError

        soup = BeautifulSoup(crawl_result.body)

        for meta_tag in soup.select("meta"):
            try:
                if meta_tag['name'].lower() == "robots":
                    if "nofollow" in meta_tag['content'].lower():
                        raise StopIteration
            except KeyError:
                pass

        for url in retrieve_links(crawl_result.url, soup):
            try:
                actions = match_url_patterns(url, host.config['crawlConfig'])
            except KeyError:
                # no crawl configuration
                self.log.error("No CrawlConfig for {}".format(host.host))
                break

            if "index" in actions or "follow" in actions:
                if self.can_fetch(host, url):
                    crawl_request = Dict()
                    crawl_request.url = url
                    crawl_request.cookies = crawl_result.cookies
                    crawl_request.method = "GET"
                    crawl_request.actions = list(actions)
                    crawl_request.referer = crawl_result.url

                    yield crawl_request.to_dict()

    def can_fetch(self, host, url):

        if not has_robots_txt(host):
            return True

        user_agent = host.user_agent or self._user_agent

        return can_fetch_url(
            "http://"+host.host+"/robots.txt",
            host.robots_txt.content,
            url,
            user_agent
        )

    def should_be_indexed(self, crawl_result):
        """

        :param crawl_request:
        :return bool:
        """
        return can_index_html(crawl_result.body,
                              ",".join(crawl_result.actions))

    def process_robots_task(self, crawl_result: Dict):
        """
        Saves fetched robots txt
        :param crawl_result:
        :return:
        """

        host = self.get_host_by_result(crawl_result)

        rt = RobotsTxt()
        rt.status = 'downloaded'
        rt.status_code = crawl_result.status_code
        rt.content = crawl_result.body
        rt.expires = now() + timedelta(10)  # 10 days

        host.robots_txt = rt
        host.save()

    def send_crawl_result_to_analysis(self, crawl_result: Dict):
        analysis_request = Dict()  # we <3 addict

        analysis_request.url = crawl_result.url
        analysis_request.body = crawl_result.body
        analysis_request.headers = crawl_result.headers
        analysis_request.crawl_time = crawl_result.crawl_time

        self.send_message(analysis_request.to_dict(), "AnalysisTask")

    def declare_queue(self, queue_name):

        return declare_queue(self._rabbitmq_url, queue_name)

    def send_crawl_request_to_host(self, crawl_request, host):

        ftr = self.declare_queue(
            "CrawlRequestQueue_{}".format(host))

        def send_msg(future):
            queue_name, exchange = future.result()
            self.send_message(crawl_request, exchange)

        ftr.add_done_callback(send_msg)

        self.publisher.add_host(host.host)

    def send_crawl_request(self, crawl_request,
                           timeout: datetime.datetime=None):

        host = self.get_host(extract_hostname(crawl_request['url']))
        if host is None:
            self.log.warning("Got a job with host I cannot find. Check debug")
            self.log.debug("Got a jbo with host I cannot find {}".format(
                repr(crawl_request)))
            return

        upsert_crawl_document(
            url=crawl_request['url'],
            url_hash=hash_url(crawl_request['url']),
            latest_request=crawl_request,
            host=extract_hostname(crawl_request['url']),
            latest_request_date=datetime.datetime.now(
                datetime.timezone.utc
            )
        )

        self.send_crawl_request_to_host(crawl_request, host.host)

    def extract_and_send_crawl_requests(self, crawl_result: Dict):
        """
        Extracts and sends crawl requests
        :param crawl_result:
        :return:
        """

        [self.send_crawl_request(request)
            for request in self.extract_requests(crawl_result)]

    def send_remove_request(self, crawl_result):
        """
        Sends delete task for Index
        :param crawl_result:
        :return:
        """
        remove_msg = Dict()
        remove_msg.url = crawl_result.url
        remove_msg.document = {}
        remove_msg.action = "delete"
        self.send_message(remove_msg.to_dict(), "IndexTask")

    @json_task
    def process_task(self, msg):
        """
        Handling messages
        :param msg:
        :return:
        """
        crawl_result = Dict(msg)
        self.log.info("Processing {}".format(crawl_result.url))
        host = self.get_host_by_result(crawl_result)
        if host is None:
            self.log.warning("Got job for host I cannot find")
            self.log.debug("Got job for host I cannot find {}".format(
                repr(crawl_result)))
            return
        try:

            if "status_code" not in crawl_result:
                raise KeyError("`status_code` not found in crawl_result "
                               + "%s json:b64:" % crawl_result.url
                               + base64.b64encode(
                                    ujson.dumps(crawl_result).encode('utf8')
                                ).decode("utf8")
                               )

            upsert_crawl_document(
                url=crawl_result.url,
                url_hash=hash_url(crawl_result.url),
                latest_result=crawl_result.to_dict(),
                latest_result_date=now(),
                latest_status_code=crawl_result.status_code
            )

            # robot - we retrieved robots.txt
            if 'robots' in crawl_result.actions:
                self.process_robots_task(crawl_result)
            else:
                def try_again_tomorrow():
                    cd = CrawlDocument.objects(
                        url_hash=hash_url(crawl_result.url)).first()

                    # try again tomorrow
                    self.log.info("Try again tomorrow: {}".format(
                        crawl_result.url))
                    if cd is not None and 'url' in cd.latest_request:
                        self.send_crawl_request(cd.latest_request,
                                                timeout=now()+timedelta(days=1)
                                                )
                    else:
                        self.send_crawl_request(
                            crawl_result.crawl_task.to_dict(),
                            timeout=now()+timedelta(days=1)
                        )

                # 200, normal processing
                if crawl_result.status_code == 200:
                    if ('follow' in crawl_result.actions
                            or "nofollow" not in crawl_result.actions):
                        self.extract_and_send_crawl_requests(crawl_result)
                    if ('index' in crawl_result.actions
                            or "noindex" not in crawl_result.actions):
                        self.send_crawl_result_to_analysis(crawl_result)

                elif 400 <= crawl_result.status_code <= 499:
                    self.send_remove_request(crawl_result)
                elif 300 <= crawl_result.status_code <= 399:
                    try_again_tomorrow()
                elif 500 <= crawl_result.status_code <= 599:
                    try_again_tomorrow()

        except NoRobotsForHostError:
            # no robots.txt or it's expired, so we create request
            # for processing
            robots_request = {
                "url": parse.urljoin(crawl_result.url, "/robots.txt"),
                "cookies": crawl_result.cookies,
                "method": "GET",
                "actions": ["robots"],
                "timeout": datetime.datetime.now(
                    datetime.timezone.utc).isoformat()
            }

            host.robots_txt = RobotsTxt(status="waiting")
            host.save()

            self.send_crawl_request_to_host(robots_request, host.host)
            self.log.warning("No robots for {}".format(host.host))
            raise RequeueMessage
        except RequeueMessage as e:
            self.log.exception(e)
            raise e
        except Exception as e:
            self.log.exception(e)
            raise RequeueMessage

        return True
