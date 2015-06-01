__author__ = 'michal'

from multiprocessing import managers
from sched import scheduler
import time
from toddler.models import Host
from datetime import datetime, timedelta
from .rabbit_sender import send_message_sync
from .crawler import match_url_patterns
from .managers import crawlmanager
import ujson


class Scheduler(object):

    def __init__(self, rabbitmq_url, exchange, routing_key, logging=None, log=None, **kwargs):
        self.rabbitmq_url = rabbitmq_url
        self.exchange = exchange
        self.routing_key = routing_key
        self.scheduler = scheduler(time.time, time.sleep)

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
                actions = match_url_patterns(crawl_root,
                                             host.config['crawlConfig'])
            except KeyError:
                actions = ['follow']
            request = {
                "url": crawl_root,
                "method": "GET",
                "actions": actions,
                "timeout": datetime.utcnow().isoformat()
            }

            host.last_crawl_job_date = datetime.utcnow()
            host.save()
            request = ujson.dumps(request)
            send_message_sync(self.rabbitmq_url, request, exchange=self.exchange,
                              routing_key=self.routing_key)

    def schedule_jobs_for_hosts(self):

        for host in Host.objects:
            if (host.last_crawl_job_date is None
                    or host.last_crawl_job_date >=
                        datetime.utcnow()+timedelta(1)):
                self.log.info("Scheduling crawl of root for {}".format(
                    host.host
                ))
                self.schedule_crawl(host)

        self.scheduler.enter(3600, 3, self.schedule_jobs_for_hosts)

    def run(self):
        reload_counter = 0
        max_reload = 10
        self.log.info("Starting up scheduler.")
        while reload_counter < max_reload:
            try:
                self.schedule_jobs_for_hosts()
                self.scheduler.run(True)
            except KeyboardInterrupt:
                self.log.info("Shutting down Scheduler")
                break
            except Exception as e:
                self.log.exception(e)
                reload_counter += 1

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):

        for p in self.scheduler.queue:
            self.scheduler.cancel(p)


