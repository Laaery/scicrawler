# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html
import random

from scrapy.exceptions import CloseSpider
from scrapy.spidermiddlewares.httperror import HttpError
from twisted.internet import task
from scrapy import signals
import csv
import time
from scrapy.http import HtmlResponse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from scrapy.utils.project import get_project_settings

# useful for handling different item types with a single interface
from itemadapter import is_item, ItemAdapter


class SciCrawlerSpiderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the spider middleware does not modify the
    # passed objects.
    def __init__(self, stats):
        self.stats = stats
        self.time = 10.0
        self.count = 0
        self.max_rejection = get_project_settings().get('MAX_REJECTION')

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        # This method is used by Scrapy to create your spiders.
        instance = cls(crawler.stats)
        crawler.signals.connect(instance.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(instance.spider_closed, signal=signals.spider_closed)
        return instance

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)
        self.tsk = task.LoopingCall(self.collect)
        self.tsk.start(self.time, now=True)
        self.doi_list = spider.doi_list
        self.total_amount = len(spider.doi_list)

    def spider_closed(self, spider):
        scrapy_count = self.stats.get_value('item_scraped_count')
        if scrapy_count is not None:
            print("Final number of scraped items:" + str(int(scrapy_count)))
            # Write the remaining dois to a csv file.
            with open(f"./unscraped/{spider.name}_{time.strftime('%Y-%m-%d')}.csv", 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerows([[doi] for doi in self.doi_list])
        else:
            print("No items scraped.")
        if self.tsk.running:
            self.tsk.stop()

    def collect(self):
        # Collect stats
        # Output to console
        scrapy_count = self.stats.get_value('item_scraped_count')
        if scrapy_count:
            print("Number of scraped items now:" + str(int(scrapy_count)))

    def process_spider_input(self, response, spider):
        # Called for each response that goes through the spider
        # middleware and into the spider.

        # Should return None or raise an exception.
        return None

    def process_spider_output(self, response, result, spider):
        # Called with the results returned from the Spider, after
        # it has processed the response.

        # Must return an iterable of Request, or item objects.
        # Pop the scraped doi [response.meta['doi']] in the list.
        if response.meta['doi'] in self.doi_list:
            self.doi_list.remove(response.meta['doi'])

        for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider):
        # Called when a spider or process_spider_input() method
        # (from other spider middleware) raises an exception.

        # Should return either None or an iterable of Request or item objects.

        # If sequentially getting too many 403, stop the spider.
        if self.count > self.max_rejection:
            raise CloseSpider('Too many 403.')

        with open(f"./log/failed_doi_{spider.name}_{time.strftime('%Y-%m-%d')}.csv", 'a', newline='') as f:
            writer = csv.writer(f)
            if isinstance(exception, HttpError):
                if response.status == 403:
                    # Keep the doi in the list, try again later.
                    print('If this shows up frequently, better stop and check if you have reached daily limit of API.')
                    self.count += 1
                else:
                    if response.meta['doi'] in self.doi_list:
                        self.doi_list.remove(response.meta['doi'])
                    writer.writerow([response.meta["doi"], response.status])
            else:
                # Pop the doi [response.meta['doi']] can not be scraped in the list.
                if response.meta['doi'] in self.doi_list:
                    self.doi_list.remove(response.meta['doi'])
                writer.writerow([response.meta["doi"], exception])
        pass

    def process_start_requests(self, start_requests, spider):
        # Called with the start requests of the spider, and works
        # similarly to the process_spider_output() method, except
        # that it doesn’t have a response associated.

        # Must return only requests (not items).
        for r in start_requests:
            yield r


class SciCrawlerDownloaderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the downloader middleware does not modify the
    # passed objects.

    user_agent = [
        "Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 5.1; Trident/4.0; GTB7.0)",
        "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)",
        "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1)",
        "Mozilla/5.0 (Windows; U; Windows NT 6.1; ) AppleWebKit/534.12 (KHTML, like Gecko) Maxthon/3.0 Safari/534.12",
        # "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; WOW64; Trident/5.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; InfoPath.3; .NET4.0C; .NET4.0E)",
        # "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; WOW64; Trident/5.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; InfoPath.3; .NET4.0C; .NET4.0E; SE 2.X MetaSr 1.0)",
        # "Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US) AppleWebKit/534.3 (KHTML, like Gecko) Chrome/6.0.472.33 Safari/534.3 SE 2.X MetaSr 1.0",
        # "Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; WOW64; Trident/5.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; InfoPath.3; .NET4.0C; .NET4.0E)",
        # "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/535.1 (KHTML, like Gecko) Chrome/13.0.782.41 Safari/535.1 QQBrowser/6.9.11079.201",
        # "Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; WOW64; Trident/5.0)",
        # "Mozilla/5.0(Macintosh;U;IntelMacOSX10_6_8;en-us)AppleWebKit/534.50(KHTML,likeGecko)Version/5.1Safari/534.50",
        # "Mozilla/5.0(Windows;U;WindowsNT6.1;en-us)AppleWebKit/534.50(KHTML,likeGecko)Version/5.1Safari/534.50",
        # "Mozilla/5.0(compatible;MSIE9.0;WindowsNT6.1;Trident/5.0;",
        # "Mozilla/4.0(compatible;MSIE8.0;WindowsNT6.0;Trident/4.0)",
        # "Mozilla/4.0(compatible;MSIE7.0;WindowsNT6.0)",
        # "Mozilla/4.0(compatible;MSIE6.0;WindowsNT5.1)",
        # "Mozilla/5.0(Macintosh;IntelMacOSX10.6;rv:2.0.1)Gecko/20100101Firefox/4.0.1",
        # "Mozilla/5.0(WindowsNT6.1;rv:2.0.1)Gecko/20100101Firefox/4.0.1",
        # "Opera/9.80(Macintosh;IntelMacOSX10.6.8;U;en)Presto/2.8.131Version/11.11",
        # "Opera/9.80(WindowsNT6.1;U;en)Presto/2.8.131Version/11.11",
        # "Mozilla/5.0(Macintosh;IntelMacOSX10_7_0)AppleWebKit/535.11(KHTML,likeGecko)Chrome/17.0.963.56Safari/535.11",
        # "Mozilla/4.0(compatible;MSIE7.0;WindowsNT5.1;Maxthon2.0)",
        # "Mozilla/4.0(compatible;MSIE7.0;WindowsNT5.1;TencentTraveler4.0)",
        # "Mozilla/4.0(compatible;MSIE7.0;WindowsNT5.1)",
        # "Mozilla/4.0(compatible;MSIE7.0;WindowsNT5.1;TheWorld)",
        # "Mozilla/4.0(compatible;MSIE7.0;WindowsNT5.1;Trident/4.0;SE2.XMetaSr1.0;SE2.XMetaSr1.0;.NETCLR2.0.50727;SE2.XMetaSr1.0)",
        # "Mozilla/4.0(compatible;MSIE7.0;WindowsNT5.1;360SE)",
        # "Mozilla/4.0(compatible;MSIE7.0;WindowsNT5.1;AvantBrowser)",
        # "Mozilla/4.0(compatible;MSIE7.0;WindowsNT5.1)"
    ]

    # proxies = ['http://183.169.89.41:8050']

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        # Called for each request that goes through the downloader
        # middleware.

        # Must either:
        # - return None: continue processing this request
        # - or return a Response object
        # - or return a Request object
        # - or raise IgnoreRequest: process_exception() methods of
        #   installed downloader middleware will be called

        # Set the user agent to avoid being blocked by the website.
        # request.headers['User-Agent'] = random.choice(self.user_agent)
        # Set the ip address to avoid being blocked by the website.
        # Use Proxy_pool to get proxies available
        # request.meta['proxy'] = random.choice(self.proxies)
        # request.meta['proxy'] = requests.get('http://127.0.0.1:5010/get/').json().get('proxy')
        return None

    def process_response(self, request, response, spider):
        # Called with the response returned from the downloader.

        # Must either;
        # - return a Response object
        # - return a Request object
        # - or raise IgnoreRequest
        return response

    def process_exception(self, request, exception, spider):
        # Called when a download handler or a process_request()
        # (from other downloader middleware) raises an exception.

        # Must either:
        # - return None: continue processing this exception
        # - return a Response object: stops process_exception() chain
        # - return a Request object: stops process_exception() chain
        pass

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)


class SciCrawlerSeleniumMiddleware:
    def __init__(self):
        self.driver = None

    @classmethod
    def from_crawler(cls, crawler):
        middleware = cls()
        crawler.signals.connect(middleware.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(middleware.spider_closed, signal=signals.spider_closed)
        return middleware

    def spider_opened(self, spider):
        self.options = Options()
        # self.options.add_argument('--headless')  # headless mode
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')
        self.options.add_argument("--window-size=1000,900")
        self.options.add_experimental_option('excludeSwitches', ['enable-automation'])
        self.options.add_experimental_option('useAutomationExtension', False)
        # Set the user agent to avoid being blocked by the website.
        # For wiley
        # self.options.add_argument(
        #     f'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
        #     f'Chrome/79.0.3945.79 Safari/537.36')
        # For acs
        self.options.add_argument(
                f'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
                                  f'Chrome/58.0.3029.110 Safari/537.36')

        self.driver = webdriver.Chrome(options=self.options)

    def spider_closed(self, spider):
        self.driver.quit()

    def process_request(self, request, spider):

        try:
            if spider.name == 'spider_wiley':
                self.driver.get(request.url)
                element = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, 'webkit-xml-viewer-source-xml')) or
                    EC.presence_of_element_located((By.ID, 'article__content')))
            elif spider.name == 'spider_rsc':
                self.driver.get(request.url)
                element = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, 'article-control')))
            elif spider.name == 'spider_acs':
                self.driver.get(request.url)
                element = WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.CLASS_NAME, 'pb-ui website-acspubs')))
        except:
            # If the page can contain 404 error,return 404.
            # if self.driver.page_source.find('Error 404'):
            #     print('Bad link.')
            #     return HtmlResponse(self.driver.current_url, request=request, encoding='utf-8', status=404)
            # else:
            return None

        else:
            # Randomly scroll down a little bit.
            # self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/{});".format(
            #     random.randint(1, 5)))
            # # Randomly sleep for 1-5 seconds.
            # time.sleep(random.randint(1, 5))
            # Return a whole html page.
            body = self.driver.page_source
            return HtmlResponse(self.driver.current_url, body=body, request=request, encoding='utf-8')
