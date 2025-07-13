import scrapy
from scrapy.loader import ItemLoader
from sci_crawler.items import Metadata
import requests
import logging
import csv
import time


class SpiderAcs(scrapy.Spider):
    name = "spider_acs"
    allowed_domains = ["pubs.acs.org"]
    logger = logging.getLogger()

    def __init__(self, doi_list_file, **kwargs):
        super().__init__()
        self.doi_list = []
        self.doi_urls = self.generate_doi_urls(doi_list_file)

    @classmethod
    def update_settings(cls, settings):
        super().update_settings(settings)
        settings.set("MONGO_COLLECTION", "acs", priority="spider")
        settings.set("DOWNLOADER_MIDDLEWARES",
                     {"sci_crawler.middlewares.SciCrawlerDownloaderMiddleware": 543,
                      "sci_crawler.middlewares.SciCrawlerSeleniumMiddleware": 600}, priority="spider")

    def start_requests(self):
        # headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
        #                           "Chrome/58.0.3029.110 Safari/537.36"}
        for doi_url in self.doi_urls:
            print(doi_url.get("url"))
            yield scrapy.Request(url=doi_url.get("url"), callback=self.parse, dont_filter=True,
                                 meta={"doi": doi_url.get("doi")})

    def parse(self, response):
        self.logger.info("Successful response from {}".format(response.url))
        loader = ItemLoader(item=Metadata(), response=response)
        loader.add_xpath("doi", '//*[@scheme="doi"]/@content')
        loader.add_xpath("title", '//*[@class="article_header-title"]/span')
        # Consider graphical abstract and abstract consisting of multiple paragraphs.
        loader.add_xpath("abstract", '//p[@class="articleBody_abstractText"]')
        loader.add_xpath("full_text", '//div[@class="article_content-left ui-resizable"]')
        return loader.load_item()

    def generate_doi_urls(self, doi_list_file):
        with open(doi_list_file, 'r') as f:
            reader = csv.reader(f)
            self.doi_list = [row[0] for row in reader]

        base_url = "https://pubs.acs.org/doi/"
        # Create a list of dict. Format as [{"doi":"", "url":""}].
        doi_urls = [{"doi": doi, "url": base_url + doi} for doi in self.doi_list]

        return doi_urls
