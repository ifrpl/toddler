__author__ = 'michal'

from sched import scheduler
from multiprocessing import Process
import time
from toddler.models import Host
from datetime import datetime, timedelta, timezone
from .rabbit_sender import send_message_sync
from .managers import crawlmanager, RabbitManager, json_task
import ujson
import dateutil.parser
from threading import Thread


class AnalysisTaskDelayQueueObserver(RabbitManager):

    @json_task
    def process_task(self, msg):
        timeout = dateutil.parser.parse(msg['timeout'])
        if timeout.tzinfo is None:
            timeout = timeout.replace(tzinfo=timezone.utc)

        if datetime.now(timezone.utc) >= timeout:

            send_message_sync(self._rabbitmq_url, ujson.dumps(msg['message']),
                              self._exchange, self._routing_key)


class AnalysisTaskDelayQueueThread(Thread):

    queue = 'Analysis'

    def __init__(self, rabbitmq_url, *args, **kwargs):

        self._rabbitmq_url = rabbitmq_url

        self.manager = AnalysisTaskDelayQueueObserver(self._rabbitmq_url,
                                                      'AnalysisTaskDelayQueue',
                                                      'AnalysisTask',
                                                      'AnalysisTask')

        super(AnalysisTaskDelayQueueThread, self).__init__(*args, **kwargs)

    def run(self):
        self.manager.run()

    def stop(self):
        self.manager.stop()


class Scheduler(object):

    def __init__(self, rabbitmq_url, exchange, routing_key, logging=None, log=None, **kwargs):
        self.rabbitmq_url = rabbitmq_url
        self.exchange = exchange
        self.routing_key = routing_key
        self.scheduler = scheduler(time.time, time.sleep)

        self.delay_queue_thread = AnalysisTaskDelayQueueThread(
            self.rabbitmq_url
        )

        if log is None:
            from toddler.logging import setup_logging
            if logging is not None:
                self.log = setup_logging(config=logging)
            else:
                self.log = setup_logging()
        else:
            self.log = log

        pass

    def schedule_crawl(self, host):
        with crawlmanager.HostLock(host.host):
            try:
                crawl_root = host.config['crawlRoot']
            except KeyError:
                crawl_root = "http://{}".format(host.host)
            try:
                actions = crawlmanager.match_url_patterns(
                    crawl_root,
                    host.config['crawlConfig']
                )
            except KeyError:
                actions = ['follow']
            request = {
                "url": crawl_root,
                "method": "GET",
                "actions": actions,
                "timeout": datetime.now(timezone.utc).isoformat()
            }

            host.last_crawl_job_date = datetime.utcnow()
            host.save()
            request = ujson.dumps(request)
            send_message_sync(self.rabbitmq_url, request,
                              exchange=self.exchange,
                              routing_key=self.routing_key)

    def schedule_jobs_for_hosts(self):

        for host in Host.objects:
            last_crawl_job_date = host.last_crawl_job_date
            if last_crawl_job_date is not None:
                if last_crawl_job_date.tzinfo is None:
                    last_crawl_job_date = (last_crawl_job_date
                                           .replace(tzinfo=timezone.utc))
            if (last_crawl_job_date is None
                    or last_crawl_job_date >=
                        (datetime.now(timezone.utc)+timedelta(1))):
                self.log.info("Scheduling crawl of root for {}".format(
                    host.host
                ))
                try:
                    self.schedule_crawl(host)
                except crawlmanager.HostLocked:
                    pass

        self.scheduler.enter(3600, 3, self.schedule_jobs_for_hosts)

    def check_delay_analysis_queue(self):



        self.delay_queue_thread.start()


    def run(self):
        reload_counter = 0
        max_reload = 10
        self.log.info("Starting up scheduler.")
        self.check_delay_analysis_queue()
        while reload_counter < max_reload:
            try:
                self.schedule_jobs_for_hosts()
                self.scheduler.run(True)
                reload_counter = 0
            except KeyboardInterrupt:
                self.log.info("Shutting down Scheduler")
                break
            except Exception as e:
                self.log.exception(e)
                reload_counter += 1

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.delay_queue_thread.stop()
        for p in self.scheduler.queue:
            self.scheduler.cancel(p)


