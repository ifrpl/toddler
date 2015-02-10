__author__ = 'michal'
import gear
import asyncio
from toddler import logging


class GearWorker(object):

    def __init__(self, gear_servers, worker_name, function, log=None):

        self.gear_servers = gear_servers
        self.function = function
        self.worker_name = worker_name
        self.worker = None
        """:type: gear.Worker"""
        self.promise = None
        self.log = logging.setup_logging(log,)

    def connect(self):
        self.worker = gear.Worker(self.worker_name)
        [self.worker.addServer(g_server) for g_server in self.gear_servers]
        self.worker.registerFunction(self.function)


    def handle_job(self, job: gear.WorkerJob):
        raise NotImplementedError

    @asyncio.coroutine
    def run(self):

        while True:

            try:
                job = self.worker.getJob()
                """:type: gear.WorkerJob"""
                try:
                    self.handle_job(job)
                    job.sendWorkComplete(job.arguments.reverse())
                except Exception as e:
                    self.log.exception(e)
                    job.sendWorkFail()
            except InterruptedError:
                return False


        return True

    def start(self):
        self.connect()
        self.promise = asyncio.async(self.run())
        return self.promise

    def stop(self):
        self.worker.stopWaitingForJobs()
