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
        """
        == Analyser task processing ==
        Analyser gets the analysis configuration for host object stored in
        MongoDB

        Then it can do several things:
        - Optionally scrape the document then
         - Export it to external resource for processing
         - or Analyse it by itself and create an IndexTask

        :param msg:
        :return:
        """
        host = Host.objects(
            host=extract_hostname(msg['url'])
        ).first().to_mongo().to_dict()

        document = Document(msg)
        try:
            parse_document(document, host['config']['analysisConfig'])
        except KeyError:
            # configuration not found, so it won't try to analyse it
            pass

        try:
            nimbusview.push_document(
                document,
                host['config']['exports']['nimbusview']['push_api_url']
            )
        except KeyError:
            # self.send_message(docu)
            # should send it to indexmanager
            pass

