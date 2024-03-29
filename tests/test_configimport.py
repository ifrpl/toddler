__author__ = 'michal'

from unittest import TestCase, mock
from mongomock import Connection
mongo_patcher = mock.patch("pymongo.MongoClient")
mock_mongo_client = mongo_patcher.start()
mock_mongo_client.return_value = Connection()
from toddler.imports.nimbuscrawl import get_configuration, convert_regexp,\
    extract_hostname

def convert_to_dict(list_of_tuples):
    d = {}
    for (key, val) in list_of_tuples:
        d[key] = val

    return d

class TestConfigImport(TestCase):
    def setUp(self):
        self.example_xml = """
            <CrawlConfig xmlns="exa:com.exalead.mercury.mami.crawl.v20" version="1427816334089" verbose="false">
                <Crawler name="properties" fetcher="properties_fetcher" crawlerServer="exa4" buildGroup="bg0" storeTextOnly="false" nthreads="20" aggressive="false" throttleTimeMS="2500" ignoreRobotsTxt="false" enableConvertProcessor="false" nearDuplicateDetector="true" patternsDetector="true" crawlSitemaps="true" disableConditionalGet="false" defaultAccept="false" defaultIndex="false" defaultFollow="false" defaultFollowRoots="true" enableSimpleSiteCollapsing="false" simpleSiteCollapsingDepth="0" mimeTypesMode="exclude" indexRedirectSources="true" smartRefresh="true" smartRefreshMinAgeS="86400" smartRefreshMaxAgeS="604800">
                    <Rules key="auto" group="lesiteimmo">
                        <Rule>
                            <Atom xmlns="exa:com.exalead.actionrules.v21" field="url" kind="suffix" norm="none" value="_ad.html" litteral="true"/>
                            <NoIndex/>
                            <NoFollow/>
                        </Rule>
                        <Rule>
                            <Atom xmlns="exa:com.exalead.actionrules.v21" field="url" kind="prefix" norm="none" value="http://www.lesiteimmo.com/" litteral="true"/>
                            <NoIndex/>
                            <Follow/>
                            <Accept/>
                        </Rule>
                        <Rule>
                            <Atom xmlns="exa:com.exalead.actionrules.v21" field="url" kind="prefix" norm="none" value="http://www.lesiteimmo.com/vente_" litteral="true"/>
                            <Index/>
                            <Follow/>
                            <Accept/>
                            </Rule>
                        <Rule>
                            <Atom xmlns="exa:com.exalead.actionrules.v21" field="url" kind="prefix" norm="none" value="http://www.lesiteimmo.com/location_" litteral="true"/>
                            <Index/>
                            <Follow/>
                            <Accept/>
                        </Rule>
                        <Rule>
                            <Atom xmlns="exa:com.exalead.actionrules.v21" field="url" kind="exact" norm="none" value="http://www.lesiteimmo.com/immobilier/\.\+/\[0-9\]\{7\}" litteral="true"/>
                            <Index/>
                            <Follow/>
                            <Accept/>
                        </Rule>
                        <Rule>
                            <Atom field="url" kind="inside" norm="none" value="alfa-romeo" litteral="true"/>
                            <NoIndex/>
                            <Follow/>
                        </Rule>
                    </Rules>
                </Crawler>
        </CrawlConfig>"""

        self.other_xml = """
            <CrawlConfig xmlns="exa:com.exalead.mercury.mami.crawl.v20" version="1427816334089" verbose="false">
                <Crawler name="properties" fetcher="properties_fetcher" crawlerServer="exa4" buildGroup="bg0" storeTextOnly="false" nthreads="20" aggressive="false" throttleTimeMS="2500" ignoreRobotsTxt="false" enableConvertProcessor="false" nearDuplicateDetector="true" patternsDetector="true" crawlSitemaps="true" disableConditionalGet="false" defaultAccept="false" defaultIndex="false" defaultFollow="false" defaultFollowRoots="true" enableSimpleSiteCollapsing="false" simpleSiteCollapsingDepth="0" mimeTypesMode="exclude" indexRedirectSources="true" smartRefresh="true" smartRefreshMinAgeS="86400" smartRefreshMaxAgeS="604800">
                    <Rules key="auto" group="fasilannonce">
                       <Rule>
                        <And xmlns="exa:com.exalead.actionrules.v21">
                         <Host val="\.\+.fasilannonce.fr" norm="norm" litteral="true"/>
                         <Or>
                          <Path val="/vente/" norm="norm" litteral="true"/>
                          <Path val="/location/" norm="norm" litteral="true"/>
                         </Or>
                         <Or>
                          <Atom field="url" kind="inside" norm="none" value="/266-" litteral="true"/>
                          <Atom field="url" kind="inside" norm="none" value="/267-" litteral="true"/>
                          <Atom field="url" kind="inside" norm="none" value="/319-" litteral="true"/>
                          <Atom field="url" kind="inside" norm="none" value="/338-" litteral="true"/>
                          <Atom field="url" kind="inside" norm="none" value="/339-" litteral="true"/>
                          <Atom field="url" kind="inside" norm="none" value="/340-" litteral="true"/>
                          <Atom field="url" kind="inside" norm="none" value="/402-" litteral="true"/>
                          <Atom field="url" kind="inside" norm="none" value="/403-" litteral="true"/>
                          <Atom field="url" kind="inside" norm="none" value="/404-" litteral="true"/>
                          <Atom field="url" kind="inside" norm="none" value="/466-" litteral="true"/>
                          <Atom field="url" kind="inside" norm="none" value="/467-" litteral="true"/>
                          <Atom field="url" kind="inside" norm="none" value="/468-" litteral="true"/>
                          <Atom field="url" kind="inside" norm="none" value="/530-" litteral="true"/>
                          <Atom field="url" kind="inside" norm="none" value="/531-" litteral="true"/>
                          <Atom field="url" kind="inside" norm="none" value="/532-" litteral="true"/>
                          <Atom field="url" kind="inside" norm="none" value="/594-" litteral="true"/>
                          <Atom field="url" kind="inside" norm="none" value="/595-" litteral="true"/>
                          <Atom field="url" kind="inside" norm="none" value="/596-" litteral="true"/>
                          <Atom field="url" kind="inside" norm="none" value="/658-" litteral="true"/>
                          <Atom field="url" kind="inside" norm="none" value="/659-" litteral="true"/>
                          <Atom field="url" kind="inside" norm="none" value="/660-" litteral="true"/>
                          <Atom field="url" kind="inside" norm="none" value="/722-" litteral="true"/>
                          <Atom field="url" kind="inside" norm="none" value="/723-" litteral="true"/>
                          <Atom field="url" kind="inside" norm="none" value="/724-" litteral="true"/>
                         </Or>
                        </And>
                        <Index/>
                        <Follow/>
                        <Accept/>
                       </Rule>
                    </Rules>
                </Crawler>
            </CrawlConfig>
        """

    def test_hostname_extraction(self):

        challenge = "http://www.lesiteimmo.com/immobilier/\.\+/\[0-9\]\{7\}"

        self.assertEqual(
            "http://www.lesiteimmo.com",
            extract_hostname(challenge)
        )

        challenge = "https://www.lesiteimmo.com/immobilier/\.\+/\[0-9\]\{7\}"

        self.assertEqual(
            "https://www.lesiteimmo.com",
            extract_hostname(challenge)
        )

        challenge = "https://www.le-site-immo.com/immobilier/\.\+/\[0-9\]\{7\}"

        self.assertEqual(
            "https://www.le-site-immo.com",
            extract_hostname(challenge)
        )

        challenge = "https://www.le-si12te-immo.com/immobilier/\.\+/\[0-9\]" \
                    "\{7\}"

        self.assertEqual(
            "https://www.le-si12te-immo.com",
            extract_hostname(challenge)
        )

        challenge = "https://www.le-si12te-immo.com/immobilier/?t=\.\+/\[0-9\]" \
                    "\{7\}"

        self.assertEqual(
            "https://www.le-si12te-immo.com",
            extract_hostname(challenge)
        )

    def test_regexp_conversion(self):

        self.assertEqual(
            "test\.com.*",
            convert_regexp("test.com\.\*")
        )

        self.assertEqual(
            "http://www\\.lesiteimmo\\.com/immobilier/.+/[0-9]{7}",
            convert_regexp(
                "http://www.lesiteimmo.com/immobilier/\.\+/\[0-9\]\{7\}"
            )
        )

        self.assertEqual(
            "http://www\\.lesiteimmo\\.com/immobilier/\?t=x\&d=c.+/-?[0-9]{7}",
            convert_regexp(
                "http://www.lesiteimmo.com/immobilier/?t=x&d=c\.\+/-\?"
                "\[0-9\]\{7\}"
            )
        )

        self.assertEqual(
            ".*",
            convert_regexp(
                "\.\*"
            )
        )


        self.assertEqual(
            "http://example\.com/.*(foo|bar)",
            convert_regexp(
                "\.\*\(foo\|bar\)",
                "http://example.com"
            )
        )

    def pattern_asserts(self, patterns):
        self.assertEqual(
            patterns[2]['actions'],
            ["index", "follow", "accept"]
        )
        self.assertEqual(
            patterns[1]['actions'],
            ["noindex", "follow", "accept"]
        )
        self.assertEqual(
            patterns[0]['patterns'][0],
            "http://www\.lesiteimmo\.com/.*_ad\.html"
        )
        self.assertEqual(
            patterns[1]['patterns'][0],
            "http://www\.lesiteimmo\.com/.*"
        )
        self.assertEqual(
            patterns[4]['patterns'][0],
            "http://www\.lesiteimmo\.com/immobilier/.+/[0-9]{7}"
        )
        self.assertEqual(
            patterns[5]['patterns'][0],
            "http://www\.lesiteimmo\.com/.*alfa-romeo.*"
        )

    def test_rule_extraction(self):
        hosts = get_configuration(self.example_xml)
        hosts = convert_to_dict(hosts)
        self.assertIn("www.lesiteimmo.com", hosts)

        self.assertEqual(len(hosts['www.lesiteimmo.com']), 6)
        patterns = hosts['www.lesiteimmo.com']
        self.pattern_asserts(patterns)

    @mock.patch("builtins.open")
    def test_configimport_script(self, mock_open):
        from toddler.decorators import _reset_already_run
        from toddler import setup
        _reset_already_run(setup)
        argv = ['--config', 'test.xml', "--type", "crawl", "--mongo-url",
                "mongodb://localhost/test"]

        import io
        def fopen(*args, **kwargs):
            return io.StringIO(self.example_xml)

        mock_open.side_effect = fopen

        from toddler.tools.configimport import main
        from toddler.models import Host

        main(*argv)

        host = Host.objects(host="www.lesiteimmo.com").first()
        """:type: Host"""
        self.assertEqual(host.host, "www.lesiteimmo.com")
        self.assertGreater(len(host.config['crawlConfig']), 0)

        self.pattern_asserts(host.config['crawlConfig'])

