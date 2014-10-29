__author__ = 'michal'
import unittest
from toddler.contentprocessors import soup
from toddler import Document
import json

class SoupContentProcessorTest(unittest.TestCase):

    def testProcessor(self):

        html = """
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
        </body>
        """

        doc = Document()

        doc.body = html

        options = """
            {
                "feature_1": [
                    {
                        "command": "select",
                        "arguments": ["p"]
                    },
                    {
                        "property": "text"
                    }
                ],
                "feature_2": [
                    {
                        "command": "select",
                        "arguments": ["div#content p:nth-of-type(2) span"]
                    },
                    {
                        "property": "text"
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
                        "property": "text"
                    }
                ]
            }
        """

        processor = soup.SoupContentProcessor(json.loads(options))
        doc = processor.parse(doc)

        self.assertEqual(len(doc.content['feature_1']), 2)
        self.assertEqual(doc.content['feature_2'][0], "Value2")
        self.assertEqual(doc.content['feature_3'][0], "Value3")



