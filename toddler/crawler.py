
from toddler.managers import RabbitManager, json_task, RequeueMessage
import requests
import addict
import ujson
import toddler
import datetime
import dateutil.parser
import re


def match_url_patterns(url, config_patterns):
    """
    Matches url against config:
    :param url: 
    :param config: 
    :return list:
    """

    def _match_pattern(config_pattern):
        for pattern in config_pattern['patterns']:
            if re.match(pattern, url):
                return list(config_pattern['actions'])
                # mongoengine returns as BaseList and it causes problems
                # for addict
        return None

    return_actions = []

    for patterns in config_patterns:
        actions = _match_pattern(patterns)
        if actions is not None:
            return_actions = actions

    return return_actions


class Crawler(RabbitManager):

    def __init__(self, crawl_result_routing_key="CrawlResult", **kwargs):

        self._crawl_result_routing_key = crawl_result_routing_key

        super(Crawler, self).__init__(**kwargs)

    @json_task
    def process_task(self, crawl_request):
        """
        Processes the task
        
        `We are in thread, no asyncio please, as we do not attach event loop
         here`
        
        :param crawl_request:
        :return:
        """

        crawl_request = addict.Dict(crawl_request)

        try:
            if "timeout" not in crawl_request:
                raise KeyError

            timeout = dateutil.parser.parse(crawl_request.timeout)

            if datetime.datetime.now(datetime.timezone.utc) <= timeout:
                raise RequeueMessage
        except (KeyError, ValueError, TypeError):
            # no timeout so do it asap
            pass

        s = requests.Session()

        if len(crawl_request.cookies) > 0:
            [s.cookies.set(name, value)
             for name, value in crawl_request.cookies.items()]
        try:
            s.headers.update({'referer': crawl_request.referer})
        except KeyError:
            pass

        try:
            method = str(crawl_request.method).upper()
        except KeyError:
            method = "GET"

        if method == "POST":
            try:
                req = s.post(crawl_request.url, data=crawl_request.data)
            except KeyError:
                try:
                    req = s.post(crawl_request.url, json=crawl_request.json)
                except KeyError:
                    req = s.post(crawl_request.url)
        else:
            req = s.get(crawl_request.url)

        """:type: requests.Response"""

        result = addict.Dict()

        result.html = req.text
        result.cookies = req.cookies.get_dict()
        result.url = crawl_request.url
        result.crawl_task = crawl_request
        result.actions = crawl_request.actions
        result.headers = req.headers
        result.status_code = req.status_code
        result.crawl_time = datetime.datetime.now(
            datetime.timezone.utc).isoformat()
        toddler.send_message_sync(
            self._rabbitmq_url,  # this is the rabbit url
            ujson.dumps(result.to_dict()),
            routing_key=self._crawl_result_routing_key
        )
