__author__ = 'michal'

from unittest import TestCase, mock
from mongomock import Connection
mongo_patcher = mock.patch("pymongo.MongoClient")
mock_mongo_client = mongo_patcher.start()
mock_mongo_client.return_value = Connection()

from toddler import analyser
from toddler.models import Host, RobotsTxt
from datetime import datetime, timezone, timedelta
import ujson


class TestAnalyser(TestCase):

    def setUp(self):

        self.analyser = analyser.Analyser(
            mongodb_url="mongodb://localhost",
            rabbitmq_url="apmq://fliv-dev",
            queue="AnalysisQueue",
            exchange="IndexTask",
            routing_key="IndexTask",
            exchange_type="",
            log=mock.Mock()
        )

        body = """
        <html>
        <head>
            <meta property="og:title" content="open graph title"/>
        </head>
        <body>
            <h1>Some Title</h1>
            <div id='content'>
                <p>
                    Feature1
                    <span>Value1</span>
                </p>
                <p>
                    Feature2
                    <span>Value2</span>
                </p>
            </div>
            <div>
                <div>
                    <div>
                        Feature3 <span>Value3</span>
                    </div>
                </div>
                <img class='someImage' src="/test.png"/>
            </div>
            <table>
                <tr>
                    <td class="f1">123</td>
                    <td>junk</td>
                </tr>
                <tr>
                    <td class="f2">456</td>
                    <td>junk</td>
                </tr>
                <tr>
                    <td class="f3">789</td>
                    <td>junk</td>
                </tr>
            </table>
        </body>
        """

        self.request = {
            "url": "http://example.com",
            "body": body,
            "headers": {},
            "crawl_time": "2015-03-24T11:43:27.746219+00:00"
        }

        plugin_config = {
            "feature_1": [
                {
                    "command": "select",
                    "arguments": ["p"]
                },
                {
                    "command": "text"
                }
            ],
            "feature_2": [
                {
                    "command": "select",
                    "arguments": ["div#content p:nth-of-type(2) span"]
                },
                {
                    "command": "text"
                }
            ],
            "feature_3": [
                {
                    "command": "select",
                    "arguments": ["img.someImage"]
                },
                {
                    "command": "find_previous_sibling",
                    "arguments": "div"
                },
                {
                    "command": "select",
                    "arguments": "span"
                },
                {
                    "command": "text"
                }
            ],
            "og_title": [
                {
                    "command": "find",
                    "arguments": "meta",
                    "kw_arguments": {"property": "og:title"}
                },
                {
                    "command": "get_attribute",
                    "arguments": "content"
                }
            ],
            "table": [
                {
                    "command": "join",
                    "arguments": [
                        [
                            {
                                "command": "select",
                                "arguments": "td.f1"
                            },
                            {
                                "command": "text"
                            }
                        ],
                        [
                            {
                                "command": "join",
                                "arguments": [
                                    [
                                        {
                                            "command": "select",
                                            "arguments": "td.f3"
                                        },
                                        {
                                            "command": "text"
                                        }
                                    ],
                                    [
                                        {
                                            "command": "select",
                                            "arguments": "td.f2"
                                        },
                                        {
                                            "command": "text"
                                        }
                                    ]
                                ]
                            }
                        ]
                    ]
                }
            ]
        }

        config = [
            {
                "plugin": {
                    "module": "toddler.contentprocessors.soup",
                    "handler": "SoupContentProcessor"
                },
                "config": plugin_config
            }
        ]

        host = {
            "host": "example.com",
            "block": False,
            "block_date": "2015-02-02T14:23:12+00:00",
            "number_of_documents": 3434,
            "config": {"analysisConfig": config},
            "ignore_robots": False,
            "robots_txt": RobotsTxt(**{
                "status": "downloaded",
                "status_code": 200,
                "content": "User-Agent: *\nAllow: /\n",
                "expires": datetime.now(timezone.utc)+timedelta(10)
            })
        }

        self.host = Host(**host)

    def test_analysis(self):

        with mock.patch("toddler.models.Host.objects") as objects:
            inst = objects.return_value
            inst.first.return_value = self.host

            with mock.patch("toddler.analyser.Analyser.send_message")\
                    as send_message:

                send_message.return_value = True
                self.analyser.process_task(
                    ujson.dumps(self.request).encode('utf8')
                )
                self.assertTrue(send_message.called)

