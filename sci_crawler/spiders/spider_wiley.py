import scrapy
import csv
from scrapy.loader import ItemLoader
from sci_crawler.items import Metadata
from scrapy.utils.project import get_project_settings
import logging
import requests


# import time


class SpiderWiley(scrapy.Spider):
    name = "spider_wiley"
    allowed_domains = ["onlinelibrary.wiley.com"]
    logger = logging.getLogger()

    def __init__(self, doi_list_file, **kwargs):
        super().__init__()
        self.doi_list = []
        self.doi_urls = self.generate_doi_urls(doi_list_file)

    @classmethod
    def update_settings(cls, settings):
        super().update_settings(settings)
        settings.set("MONGO_COLLECTION", "wiley", priority="spider")
        settings.set("DOWNLOADER_MIDDLEWARES",
                     {"sci_crawler.middlewares.SciCrawlerDownloaderMiddleware": 543,
                      "sci_crawler.middlewares.SciCrawlerSeleniumMiddleware": 600}, priority="spider")

    def start_requests(self):

        for doi_url in self.doi_urls:
            yield scrapy.Request(url=doi_url.get("url"), callback=self.parse, dont_filter=True,
                                 meta={"doi": doi_url.get("doi")})

    def parse(self, response):
        self.logger.info("Successful response from {}".format(response.url))
        loader = ItemLoader(item=Metadata(), response=response)
        # For XML format.
        # loader.add_xpath("doi", '//publicationmeta[@level="unit"]/doi/text()')
        # loader.add_xpath("title", '//contentmeta/titlegroup/title[@type="main"]')
        # # Consider graphical abstract and abstract consisting of multiple paragraphs.
        # loader.add_xpath("abstract", '//abstractgroup/abstract[@type="main"]/descendant::p')

        # For HTML format. Denote the following code as comment if you want to use HTML format.
        loader.add_xpath("doi", '//meta[@name="dc.identifier"]/@content')
        loader.add_xpath("title", '//meta[@name="citation_title"]/@content')
        # Consider graphical abstract and abstract consisting of multiple paragraphs.
        loader.add_xpath("abstract", '//*[@class="abstract-group "]/descendant::p')
        return loader.load_item()

    def generate_doi_urls(self, doi_list_file):
        with open(doi_list_file, 'r') as f:
            reader = csv.reader(f)
            self.doi_list = [row[0] for row in reader]
        # XML format.
        # base_url = "https://onlinelibrary.wiley.com/doi/full-xml/"

        # For those doi not provided with full-xml, use the following url.
        base_url = "https://onlinelibrary.wiley.com/doi/"

        # Create a list of dict. Format as [{"doi":"", "url":""}].
        doi_urls = [{"doi": doi, "url": base_url + doi} for doi in self.doi_list]

        return doi_urls
