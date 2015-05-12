__author__ = 'michal'

from . import RabbitManager, json_task
from toddler.models import IndexDocument, connect, hash_url
from . import crawlmanager


class IndexManager(RabbitManager):
    def __init__(self, mongo_url, *args, **kwargs):
        """
        = Index Manager =

        Gets document from rabbitmq and writes it to MongoDB

        Configuration parameters:
        :param mongo_url: Url to mongodb
        :param rabbitmq_url: Url to rabbitmq
        -
        """
        self.mongo_url = mongo_url
        connect(host=mongo_url)
        super(IndexManager, self).__init__(*args, **kwargs)

    def delete_document(self, index_task):

        IndexDocument.objects(url=index_task['url']).delete()

    def upsert_document(self, index_task):

        update_dict = {
            "set__url": index_task['url'],
            "set__url_hash": hash_url(index_task['url']),
            "set__host": crawlmanager.extract_hostname(index_task['url']),
            "set__meta_data": index_task['document']['meta_data'],
            "set__features": index_task['document']['features']
        }

        IndexDocument.objects(url=index_task['url']).update_one(
            upsert=True,
            **update_dict
        )

    @json_task
    def process_task(self, msg):

        if msg['action'] == "delete":
            self.delete_document(msg)
        elif msg['action'] == "upsert" or msg['action'] == "insert":
            self.upsert_document(msg)


