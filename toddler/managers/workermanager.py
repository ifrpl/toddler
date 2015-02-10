__author__ = 'michal'

import gear
import pika
from . import RabbitManager


class DocumentWorkerManager(RabbitManager):

    def __init__(self, gearman_servers, *args, **kwargs):
        self.gearman_servers = gearman_servers
        super(DocumentWorkerManager, self).__init__(*args, **kwargs)

    def process_task(self, msg):

        print("Processing task...")
        client = gear.Client()
        [client.addServer(g_server) for g_server in self.gearman_servers]
        client.waitForServer()
        print("Connected to gear server")
        job = gear.Job("document", msg)
        client.submitJob(job)

