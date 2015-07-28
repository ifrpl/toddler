__author__ = 'michal'

from datetime import datetime, timedelta, timezone

import ujson

from toddler.managers.crawlmanager import extract_hostname

from . import Document, send_message_sync
from .contentprocessors import parse_document
from .exports import nimbusview
from .managers import RabbitManagerWithMongoDb, json_task
from .models import Host


class Analyser(RabbitManagerWithMongoDb):

    def send_message(self, msg, exchange=None, routing_key=None):

        send_message_sync(
            self._rabbitmq_url,
            msg,
            exchange=exchange or self._exchange,
            routing_key=routing_key or self._routing_key
        )

    @json_task
    def process_task(self, msg, push_api=None, connector=None):
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
            # document.features['source'] =\
            #     host['config']['exports']['nimbusview']['source']

            if connector is None:
                connector = \
                    host['config']['exports']['nimbusview']['connector']


            if push_api is None:
                push_api =\
                    host['config']['exports']['nimbusview']['push_api_url']
            nimbusview.push_document(
                document,
                push_api,
                connector
            )
        except KeyError:
            self.log.error("No export config for {}".format(msg['url']))
            self.send_message(ujson.dumps(
                {
                    'delay_reason': "No export config",
                    'timeout': (datetime.now(timezone.utc)
                                + timedelta(hours=1)).isoformat(),
                    'message': msg
                }
            ), 'AnalysisTask', 'delay')
