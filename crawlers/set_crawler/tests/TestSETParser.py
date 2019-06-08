import os
from pathlib import Path

from scrapy.http import HtmlResponse
from betamax import Betamax
from betamax.fixtures.unittest import BetamaxTestCase

from ..set_crawler.spiders.symbol_info_spider import SymbolInfoSpider

with Betamax.configure() as config:
    cassette_dir = os.path.join(str(Path.home()), 'cassettes')

    if not os.path.exists(cassette_dir):
        os.mkdir(cassette_dir)

    config.cassette_library_dir = os.path.join(str(Path.home()), 'cassettes')
    config.preserve_exact_body_bytes = True


class TestSETParser(BetamaxTestCase):

    spider = SymbolInfoSpider()

    def _url2response(self, url):
        response = self.session.get(url)

        return HtmlResponse(body=response.content, url=url)

    def test_parse_directory(self):
        """
        Test company directory page such as
        https://www.set.or.th/set/commonslookup.do?language=en&country=TH&prefix=A
        """

        number_prefix_url = "https://www.set.or.th/set/commonslookup.do?" \
                            "language=en&country=US&prefix=NUMBER"
        scrapy_response = self._url2response(number_prefix_url)

        follow_reqs = self.spider.parse(scrapy_response)
        follow_urls = [r.url for r in follow_reqs]

        # Follow company profile pages
        self.assertTrue('https://www.set.or.th/set/companyprofile.do?'
                        'symbol=2S&ssoPageId=4&language=en&country=US' in follow_urls)
        self.assertTrue('https://www.set.or.th/set/companyprofile.do?'
                        'symbol=7UP&ssoPageId=4&language=en&country=US' in follow_urls)

        # Follow major shareholders pages
        self.assertTrue('https://www.set.or.th/set/companyholder.do?'
                        'symbol=2S&ssoPageId=4&language=en&country=US' in follow_urls)
        self.assertTrue('https://www.set.or.th/set/companyholder.do?'
                        'symbol=7UP&ssoPageId=4&language=en&country=US' in follow_urls)

    def test_parse_comp_profile(self):
        url = "https://www.set.or.th/set/companyprofile.do?symbol=MINT&ssoPageId=4&language=en&country=US"
        scrapy_response = self._url2response(url)

        profile = list(self.spider.parse_comp_profile(scrapy_response))

        self.assertEqual(len(profile), 1)

        profile = profile[0]

        self.assertEqual(profile["type"], "info")
        self.assertEqual(profile["symbol"], "MINT")
        self.assertEqual(profile["company"], "MINOR INTERNATIONAL PUBLIC COMPANY LIMITED")
        self.assertEqual(profile["market"], "SET")
        self.assertEqual(profile["industry"], "Agro & Food Industry")
        self.assertEqual(profile["sector"], "Food & Beverage")
        self.assertEqual(profile["first_date"], "14 Oct 1988")
        self.assertEqual(profile["address"], "BERLI JUCKER HOUSE,FL16, 99 SUKHUMVIT 42 RD, KHLONG TOEI Bangkok")
        self.assertEqual(profile["auth_capital"], "4,849,860,006.00 Baht")
        self.assertEqual(profile["paid_up_capital"], "4,618,914,291.00 Baht")

    def test_parse_major_holders(self):
        url = "https://www.set.or.th/set/companyholder.do?symbol=MINT&ssoPageId=6&language=en&country=US"
        scrapy_response = self._url2response(url)

        holders = list(self.spider.parse_comp_holders(scrapy_response))

        prev_rank = 0
        for h in holders:
            self.assertGreaterEqual(h["share_num"], 1000000)
            self.assertEqual(h["type"], "holder")
            self.assertEqual(h["rank"], prev_rank+1)
            prev_rank = h["rank"]

        biggest_holder = holders[0]
        self.assertEqual(biggest_holder["name"], "บริษัท ไมเนอร์ โฮลดิ้ง (ไทย) จำกัด")
