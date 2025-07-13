import scrapy
import csv
from scrapy.loader import ItemLoader
from sci_crawler.items import Metadata
import requests
import logging
import csv
import time
from crossref.restful import Works, Etiquette
import re


class SpiderRsc(scrapy.Spider):
    name = "spider_rsc"
    allowed_domains = ["pubs.rsc.org"]
    logger = logging.getLogger()

    def __init__(self, doi_list_file, **kwargs):
        super().__init__()
        self.doi_list = []
        self.doi_urls = self.generate_doi_urls(doi_list_file)

    @classmethod
    def update_settings(cls, settings):
        super().update_settings(settings)
        settings.set("MONGO_COLLECTION", "rsc", priority="spider")
        # settings.set("DOWNLOADER_MIDDLEWARES",
        #              {"sci_crawler.middlewares.SciCrawlerDownloaderMiddleware": 543,
        #               "sci_crawler.middlewares.SciCrawlerSeleniumMiddleware": 600}, priority="spider")

    def start_requests(self):
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                                 "Chrome/111.0.0.0 Safari/537.36 Edg/111.0.1661.41"}
        # "cookie": {"user.uuid.v2": "xxx"} }
        # Set up Crossref API
        my_etiquette = Etiquette('SciTDM', '1.0', 'N/A',
                                 'le_lin@foxmail.com')
        work = Works(etiquette=my_etiquette)

        with open(f"./doi_list/doi_urls_{self.name}.csv", 'w', newline='') as f:
            writer = csv.writer(f)
            for doi_url in self.doi_urls:
                doi_url = {"doi": doi_url.get("doi"), "url": re.sub(r'articlepdf', 'articlelanding', work.doi(doi_url.get("doi")).get('link')[0].get('URL'))}

                writer.writerow([doi_url.get("doi"), doi_url.get("url")])
                yield scrapy.Request(url=doi_url.get("url"), callback=self.parse, dont_filter=True, headers=headers,
                                 meta={"doi": doi_url.get("doi")})

    def parse(self, response):
        self.logger.info("Successful response from {}".format(response.url))
        loader = ItemLoader(item=Metadata(), response=response)
        # loader.add_xpath("doi", '//*[@name="citation_doi"]/@content')
        loader.add_xpath("doi", '//*[@name="DC.Identifier"]/@content')
        loader.add_xpath("title", '//*[@name="DC.title"]/@content')
        # Consider graphical abstract and abstract consisting of multiple paragraphs.
        loader.add_xpath("abstract", '//*[@class="capsule__text"]/descendant::p')
        # loader.add_xpath("full_text", '//*[@id="pnlArticleContent"]/descendant::p | //*['
        #                               '@id="pnlArticleContent"]/descendant::h2 | //*['
        #                               '@id="pnlArticleContent"]/descendant::h3')

        # loader.add_xpath("doi", '//*[@name="citation_doi"]/@content')
        # loader.add_xpath("title", '//*[@property="og:title"]/@content')
        # loader.add_xpath("abstract", '//*[@class="capsule__text"]/descendant::p')
        # loader.add_xpath("full_text", '//*[@id="pnlArticleContent"]/descendant::p')
        return loader.load_item()

    def generate_doi_urls(self, doi_list_file):
        with open(doi_list_file, 'r') as f:
            reader = csv.reader(f)
            self.doi_list = [row[0] for row in reader]
        # Use redirecting links to land on target publisher's website.
        # base_url = "http://xlink.rsc.org/?DOI="
        # base_url = "http://dx.doi.org/"

        # Save doi_urls to a csv file.
        doi_urls = [{"doi": doi, "url": "wait"} for doi in self.doi_list]
        return doi_urls
