import scrapy
import csv
from scrapy.loader import ItemLoader
from sci_crawler.items import Metadata
from scrapy.utils.project import get_project_settings
import logging
import requests
import time


class SpiderSpringerApi(scrapy.Spider):
    name = "spider_springer_api"
    allowed_domains = ["api.springernature.com"]
    logger = logging.getLogger()

    def __init__(self, doi_list_file, **kwargs):
        super().__init__()
        self.doi_list = []
        self.doi_urls = self.generate_doi_urls(doi_list_file)
        self.api_key = get_project_settings().get("SPRINGER_API_KEY")

    @classmethod
    def update_settings(cls, settings):
        super().update_settings(settings)
        settings.set("MONGO_COLLECTION", "springer", priority="spider")

    def start_requests(self):
        # headers = { "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)
        # Chrome/116.0.0.0 Safari/537.36 Edg/116.0.1938.76" "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        # "cookie": {"user.uuid.v2": "xxx"} }
        for doi_url in self.doi_urls:
            url = doi_url.get("url") + "&api_key=" + self.api_key
            yield scrapy.Request(url=url, callback=self.parse, dont_filter=True, meta={"doi": doi_url.get("doi")})

    def parse(self, response):
        self.logger.info("Successful response from {}".format(response.url))
        loader = ItemLoader(item=Metadata(), response=response)
        loader.add_value("doi", response.json()["records"][0]["doi"])
        loader.add_value("title", response.json()["records"][0]["title"])
        loader.add_value("abstract", response.json()["records"][0]["abstract"])

        return loader.load_item()

    def generate_doi_urls(self, doi_list_file):
        with open(doi_list_file, 'r') as f:
            reader = csv.reader(f)
            self.doi_list = [row[0] for row in reader]

        base_url = "https://api.springernature.com/meta/v2/json?q=doi:"
        # Create a list of dict. Format as [{"doi":"", "url":""}].
        doi_urls = [{"doi": doi, "url": base_url + doi} for doi in self.doi_list]

        return doi_urls
