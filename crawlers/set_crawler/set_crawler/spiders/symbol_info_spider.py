import os
import re
import locale
import string
import logging
from typing import *

import scrapy
from scrapy.http import Response
from scrapy.selector.unified import Selector

locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')


class SymbolInfoSpider(scrapy.Spider):
    """
    Spider to scrape basic information and major holders of symbols
    in the Stock Exchange of Thailand (SET)
    """

    name = "set_crawler"
    symbol_pattern = re.compile(r"symbol=(\w*)&")

    def start_requests(self):
        url_prefix = "https://www.set.or.th/set/commonslookup.do" \
                     "?language=en&country=TH"

        run_mode = getattr(self, "mode", "test")
        if run_mode == "test":
            queries = ["NUMBER"]
        elif run_mode == "full":
            queries = ["NUMBER"] + list(string.ascii_uppercase)
        else:
            raise ValueError(f"Unknown mode {run_mode}")

        self.log(f"Start spider with the mode: {run_mode}\n",
                 level=logging.INFO)

        for q in queries:
            url = f"{url_prefix}&prefix={q}"
            yield scrapy.Request(url=url, callback=self.parse)

    def _save_original(self, symbol: str, data_dir: str, page_type: str, response: Response):
        filename = os.path.join(data_dir, f"{symbol}-{page_type}.html")

        try:
            with open(filename, 'wb') as f:
                f.write(response.body)
            self.log('Saved file %s' % filename, level=logging.DEBUG)
            return True
        except Exception as e:
            self.log(f"Cannot save {filename} because '{e}'", level=logging.WARNING)
            return False

    def _extract_comp_name(self, response: Response):
        symbol_corp = response.css("div h3::text").get()
        if symbol_corp is None:
            self.log("Cannot get symbol in major holders page",
                     level=logging.WARNING)
            symbol = "Unknown"
            company = "Unknown"
            self.log(f"Cannot extract symbol and company for {response.url}", level=logging.WARNING)
        else:
            symbol_corp_spl = symbol_corp.split(":")
            symbol = symbol_corp_spl[0].strip()
            company = symbol_corp_spl[1].strip()
        return symbol, company

    def parse(self, response: Response):
        """
        Parse symbol directory pages such as
        https://www.set.or.th/set/commonslookup.do?language=en&country=TH&prefix=A
        """
        symbol_rows = response.css("tr[valign=top]")
        for row in symbol_rows:
            comp_profile_page = row.css("td a::attr(href)").get()
            comp_holders_page = comp_profile_page \
                .replace("companyprofile", "companyholder")

            yield response.follow(comp_profile_page,
                                  callback=self.parse_comp_profile)
            yield response.follow(comp_holders_page,
                                  callback=self.parse_comp_holders)

    def parse_comp_profile(self, response: Response) -> Dict:
        """
        Parse company profile page such as
        https://www.set.or.th/set/companyprofile.do?symbol=A&ssoPageId=4&language=en&country=TH
        """
        def extract_text(row_sel: Selector, query: str) -> List[str]:
            vals = row_sel.css(query).getall()

            if len(vals) > 0:
                return [v.strip() for v in vals]
            else:
                return vals

        def get_key(row_sel: Selector) -> Optional[str]:
            strong_key = extract_text(row_sel, "div div strong::text")
            if len(strong_key) == 1:
                return strong_key[0]
            else:
                sub_key = extract_text(row_sel, "div div::text")
                if len(sub_key) == 2:
                    return sub_key[0]
                else:
                    return None

        def get_val(row_sel: Selector) -> Optional[str]:
            vals = extract_text(row_sel, "div div::text")
            if len(vals) == 1:
                return vals[0]
            elif len(vals) == 2:
                return vals[1]
            else:
                return None

        symbol, company = self._extract_comp_name(response)

        data_dir = getattr(self, "data_dir", None)
        if data_dir is not None:
            self._save_original(symbol=symbol,
                                data_dir=data_dir,
                                page_type="info",
                                response=response)

        rows = response.css("table tr td div.row")

        symbol_info = {"type": "info",
                       "symbol": symbol,
                       "company": company}
        for row in rows:
            if get_key(row) == "Market":
                symbol_info["market"] = get_val(row).upper()
            elif get_key(row) == "Industry":
                symbol_info["industry"] = get_val(row)
            elif get_key(row) == "Sector":
                symbol_info["sector"] = get_val(row)
            elif get_key(row) == "First Trade Date":
                symbol_info["first_date"] = get_val(row)
            elif get_key(row) == "Address":
                symbol_info["address"] = get_val(row)
            elif get_key(row) == "Authorized Capital" \
                    and "auth_capital" not in symbol_info:
                symbol_info["auth_capital"] = get_val(row)
            elif get_key(row) == "Paid-up Capital" \
                    and "paid_up_capital" not in symbol_info:
                symbol_info["paid_up_capital"] = get_val(row)
            elif get_key(row) == "Paid-up Capital" \
                    and "paid_up_capital" not in symbol_info:
                symbol_info["paid_up_capital"] = get_val(row)
        yield symbol_info

    def parse_comp_holders(self, response: Response) -> Iterator[Dict]:
        """
        Parse company major holders page such as
        https://www.set.or.th/set/companyholder.do?symbol=A&ssoPageId=6&language=en&country=TH
        """

        symbol, company = self._extract_comp_name(response)

        data_dir = getattr(self, "data_dir", None)
        if data_dir is not None:
            self._save_original(symbol=symbol,
                                data_dir=data_dir,
                                page_type="holders",
                                response=response)

        holder_rows = response.css("tbody tr")
        for row in holder_rows:
            holder_info = row.css("*::text").getall()
            holder_info = [t.strip() for t in holder_info if len(t.strip()) > 0]
            if len(holder_info) != 4:
                self.log(f"Suspicious format: {holder_info}", level=logging.WARNING)
                continue
            yield {
                "type": "holder",
                "symbol": symbol,
                "company": company,
                "rank":  int(holder_info[0].replace(".", "")),
                "name": holder_info[1],
                "share_num": locale.atoi(holder_info[2]),
                "share_pct": float(holder_info[3])
            }
