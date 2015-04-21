__author__ = 'michal'
import requests
from addict import Dict
from bs4 import BeautifulSoup, Tag
from urllib.parse import urljoin
from datetime import datetime
from toddler.managers.indexmanager import hash_url
from toddler.logging import setup_logging
from urllib.parse import urlencode

__all__= ['get_documents']


def _extract_hit(tag: Tag):

    meta_doc = Dict()

    meta_doc.url = tag['url']
    meta_doc.url_hash = hash_url(tag['url'])
    to_datetime = lambda x: datetime.strptime(x, "%m/%d/%Y %H:%M:%S")

    def _parse_meta(meta_tag: Tag):
        nonlocal meta_doc
        if meta_tag['name'] == 'lastmodifieddate':
            meta_doc.features[meta_tag['name']] = [to_datetime(
                meta_tag.text.strip()
            )]
        else:
            meta_doc.features[meta_tag['name']] = [meta_tag.text]

    [_parse_meta(meta) for meta in tag.find_all("Meta")]

    return meta_doc.to_dict()


def get_documents(search_url, params: dict, nb_rows=600, per_page=100):

    log = setup_logging()
    params = Dict(**params)
    params.language = "en"
    params.synthesis = "disabled" # no synthesis
    params.hf =  per_page
    context = None
    i = 0
    for x in range(0, nb_rows, per_page):
        url = urljoin(search_url, "/search-api/search")
        params.start = x
        params.context = context
        while True:
            response = requests.get(url, params=params.to_dict())
            """:type response: requests.Response"""
            if response.status_code != 200:
                log.error("Got 500: %s" % url)
                log.debug(params.to_dict())
                log.debug(response.text)
                continue

            """:type response: requests.Response"""
            doc = BeautifulSoup(response.text.encode("utf8"), ['lxml', 'xml'])
            context = doc.Answer['context']
            if int(doc.Answer['nhits']) > 0:
                for hit in doc.find_all("Hit"):
                    log.info("Extracted %d document" % i)
                    i += 1
                    yield _extract_hit(hit)

            break

    return