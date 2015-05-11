__author__ = 'michal'
import unittest
from toddler.contentprocessors import soup
from toddler import Document
import json


class SoupContentProcessorTest(unittest.TestCase):

    def setUp(self):

        self.html = """
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

        doc = Document()

        doc.body = self.html
        self.doc = doc
        self.options = """
            {
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
        """

    def test_processor(self):

        processor = soup.SoupContentProcessor(json.loads(self.options))
        doc = processor.parse(self.doc)

        self.assertEqual(len(doc.features['feature_1']), 2)
        self.assertEqual(doc.features['feature_2'][0], "Value2")
        self.assertEqual(doc.features['feature_3'][0], "Value3")
        self.assertEqual(doc.features['og_title'][0], "open graph title")

        self.assertEqual(doc.features['table'][1], "789")

        def _raises():
            options = """
            {
                "feature_1": [
                    {
                        "command": "select",
                        "arguments": ["p"]
                    },
                    {
                        "command": "magic"
                    }
                ]
            }
            """

            processor = soup.SoupContentProcessor(json.loads(options))
            doc = processor.parse(self.doc)

        self.assertRaises(NotImplementedError, _raises)