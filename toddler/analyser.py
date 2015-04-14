__author__ = 'michal'

from .managers import json_task, RabbitManagerWithMongoDb
from .contentprocessors import parse_document
from .models import Host
from toddler.managers.crawlmanager import extract_hostname
from . import Document, send_message_sync
import ujson
from .exports import nimbusview


class Analyser(RabbitManagerWithMongoDb):

    def send_message(self, msg):

        send_message_sync(
            self._rabbitmq_url,
            msg,
            exchange=self._exchange,
            routing_key=self._routing_key
        )

    @json_task
    def process_task(self, msg):

        host = Host.objects(host=extract_hostname(msg['url'])).first().to_mongo().to_dict()

        document = Document(msg)
        features = parse_document(document, host['config']['analysisConfig'])
        document.features = features

        nimbusview.push_document(
            document,
            host['config']['exports']['nimbusview']['push_api_url']
        )

        # self.send_message(ujson.dumps(index_task))

