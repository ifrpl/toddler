__author__ = 'michal'
import datetime
from mongoengine import connect, Document, StringField, \
    DateTimeField, IntField, DictField, BooleanField, EmbeddedDocument,\
    EmbeddedDocumentField, URLField, DynamicDocument, signals

import hashlib

__all__ = ['RobotsTxt', 'Host', 'connect', 'upsert_crawl_document', 'hash_url']

from functools import reduce
from hashlib import md5


def handler(event):
    """Signal decorator to allow use of callback functions as class decorators."""

    def decorator(fn):
        def apply(cls):
            event.connect(fn, sender=cls)
            return cls

        fn.apply = apply
        return fn

    return decorator


def hash_url(url):
    """
    Creates md5 hash string from given string
    :param url:
    :return str:
    """
    h = md5()
    h.update(url.encode("utf8"))
    return h.hexdigest()


class RobotsTxt(EmbeddedDocument):

    status = StringField(choices=['waiting', 'downloaded', 'none'],
                         default='none')
    status_code = IntField()
    content = StringField()
    expires = DateTimeField()


class Host(Document):

    host = StringField(unique=True)
    user_agent = StringField(default=None)
    agressive_crawl = BooleanField(default=None)
    request_delay = IntField(default=0)
    block = BooleanField()
    block_date = DateTimeField()
    number_of_documents = IntField()
    number_of_indexed_documents = IntField()
    config = DictField()
    ignore_robots = BooleanField(default=False)
    robots_txt = EmbeddedDocumentField(RobotsTxt, default=RobotsTxt)
    last_crawl_job_date = DateTimeField()

    def increment_documents(self, value=1):
        self.objects(host=self.host).update_one(inc__number_of_documents=value)

    def increment_indexed_documents(self, value=1):
        self.objects(host=self.host).update_one(inc__number_of_documents=value)


@handler(signals.pre_save)
def add_url_hash(sender, document, **kwargs):
    if document.url_hash == "":
        document.url_hash = hash_url(document.url)


@handler(signals.pre_save)
def update_last_modified(sender, document, **kwargs):
    document.last_modified = datetime.datetime.now(datetime.timezone.utc)


@add_url_hash.apply
@update_last_modified.apply
class CrawlDocument(Document):

    host = StringField(required=True)
    url = URLField(required=True, unique=True)
    url_hash = StringField(default=None)
    create_date = DateTimeField(default=datetime.datetime.now())
    last_modified = DateTimeField()
    latest_request_date = DateTimeField()
    latest_result_date = DateTimeField()
    latest_request = DictField()
    latest_result = DictField()
    latest_status_code = IntField(default=0)


def to_set_keywords(**kwargs):

    def _rewrite_keys(d, items):
        d["set__"+items[0]] = items[1]
        return d

    return reduce(_rewrite_keys, kwargs.items(), {})


@add_url_hash.apply
@update_last_modified.apply
class IndexDocument(Document):

    url = URLField(required=True, unique=True)
    url_hash = StringField(default=None)
    host = StringField()
    meta_data = DictField()
    features = DictField()
    deleted = BooleanField(default=False)
    last_modified = DateTimeField()

    @classmethod
    def upsert(cls, url_hash, values):
        kws = to_set_keywords(**values)
        cls.objects(url_hash=url_hash).update_one(
            upsert=True,
            **kws
        )


def upsert_crawl_document(*args, **kwargs):
    """
    Helper for upserting crawl documents

    upsert_crawl_document(url="http:///", latest_status_code=200)

    :param args:
    :param kwargs:
    :return:
    """
    url = kwargs['url']

    def _rewrite_keys(d, items):
        d["set__"+items[0]] = items[1]
        return d

    set_kw = reduce(_rewrite_keys, kwargs.items(), {})

    return CrawlDocument.objects(url=url).update_one(
        upsert=True,
        **set_kw
    )