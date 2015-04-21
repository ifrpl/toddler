__author__ = 'michal'

import requests
from toddler import Document
from urllib.parse import urljoin
import uuid


def push_document(document: Document, push_api_url, connector="properties"):
    """

    :param document:
    :param push_api_url:
    :param connector:
    :return requests.Response:
    """
    papi_url = urljoin(push_api_url,
                       "/papi/4/connectors/%s/add_documents" % connector)
    doc_id = str(uuid.uuid4()).replace("-", "")

    fn = lambda x: "PAPI_%s:%s" % (doc_id, x)

    push = {
        fn("uri"): document.url + "",
    }

    def _add_meta(name, val):
        meta_name = lambda x: fn("meta:%s") % x
        push[meta_name(name)] = ('', val)

    [_add_meta(key, val) for key, val in document.features.items()]

    # response_session = requests.get(
    #     urljoin(papi_url,
    #             "/papi/4/connectors/%s/get_current_session_id" % connector)
    # )

    response = requests.post(
        papi_url,
        files=push
    )

    return response


