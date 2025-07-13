import scrapy
import csv
from scrapy.loader import ItemLoader
from sci_crawler.items import Metadata
from scrapy.utils.project import get_project_settings
import logging
import pdf_tools
import pdfquery


class SpiderWileyApi(scrapy.Spider):
    name = "spider_wiley_api"
    allowed_domains = ["api.wiley.com"]
    logger = logging.getLogger()

    def __init__(self, doi_list_file, **kwargs):
        super().__init__()
        self.doi_list = []
        self.doi_urls = self.generate_doi_urls(doi_list_file)
        self.api_key = get_project_settings().get("WILEY_API_KEY")

    @classmethod
    def update_settings(cls, settings):
        super().update_settings(settings)
        settings.set("MONGO_COLLECTION", "test", priority="spider")

    def start_requests(self):
        headers = {"Wiley-TDM-Client-Token": self.api_key,
                   "User-Agent": 'curl/8.0.1'}
        for doi_url in self.doi_urls:
            yield scrapy.Request.from_curl(curl_command=f"curl -H 'WileyTDMClientToken':{self.api_key} {doi_url.get('url')}",
                                           callback=self.parse, dont_filter=True,
                                           meta={"doi": doi_url.get("doi"), 'dont_redirect': False})
            # yield scrapy.Request(url=doi_url.get('url'), callback=self.parse, dont_filter=True, headers=headers,
            #                      meta={"doi": doi_url.get("doi"), 'dont_redirect': False})

    def parse(self, response):
        self.logger.info("Successful response from {}".format(response.url))
        pdf = pdfquery.PDFQuery(response.body)
        print(response.body)
        response = response.replace(body=pdf.tree)
        loader = ItemLoader(item=Metadata(), response=response)
        loader.add_value("doi", )
        loader.add_value("title", )
        loader.add_value("abstract", )
        return loader.load_item()

    def generate_doi_urls(self, doi_list_file):
        with open(doi_list_file, 'r') as f:
            reader = csv.reader(f)
            self.doi_list = [row[0] for row in reader]

        base_url = "https://api.wiley.com/onlinelibrary/tdm/v1/articles/"
        # Create a list of dict. Format as [{"doi":"", "url":""}].
        # Replace '/' in doi with '%'.
        doi_urls = [{"doi": doi, "url": base_url + doi.replace('/', '%')} for doi in self.doi_list]

        return doi_urls
