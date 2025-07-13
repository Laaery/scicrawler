"""This spider is designated to scrape papers from Elsevier API."""
import scrapy
import csv
from scrapy.loader import ItemLoader
from sci_crawler.items import Metadata
from scrapy.utils.project import get_project_settings
import requests
import logging
import csv
import xml.etree.ElementTree as ET
import re
import os
import time


class SpiderElsApi(scrapy.Spider):
    name = "spider_elsevier_api"
    allowed_domains = ["api.elsevier.com"]
    logger = logging.getLogger()

    def __init__(self, doi_list_file, **kwargs):
        super().__init__()
        self.doi_list = []
        self.doi_urls = self.generate_doi_urls(doi_list_file)
        self.api_key = get_project_settings().get("ELSEVIER_API_KEY")

    @classmethod
    def update_settings(cls, settings):
        super().update_settings(settings)
        settings.set("MONGO_COLLECTION", "test", priority="spider")
        # elsevier_full_text_v4

    def start_requests(self):
        headers = {"X-ELS-APIKey": self.api_key, "Accept": "text/xml"}
        for doi_url in self.doi_urls:
            yield scrapy.Request(url=doi_url.get("url"), callback=self.parse, dont_filter=True, headers=headers,
                                 meta={"doi": doi_url.get("doi")})

    def parse(self, response):
        """
        Parse the response from Elsevier API. Note that the response.body is in XML format, but the full text might
        be structured in XML format or packed in raw text. The raw text is a complete mess-up. Alternatively,
        extract the full text from PDF is a better option, but it requires OCR or other CV techniques to extract the
        text from PDF.

        Arguments:
            response(scrapy.Response): response from Elsevier API

        Returns:
            ItemLoader: ItemLoader object
        """
        self.logger.info("Successful response from {}".format(response.url))
        loader = ItemLoader(item=Metadata(), response=response)
        loader.add_xpath('doi', '//prism:doi', namespaces={'prism': "http://prismstandard.org/namespaces/basic/2.0/"})
        loader.add_xpath("title", '//dc:title', namespaces={'dc': "http://purl.org/dc/elements/1.1/"})
        loader.add_xpath("abstract", '//dc:description', namespaces={'dc': "http://purl.org/dc/elements/1.1/"})

        root = ET.fromstring(response.body)

        # Extract full text from structured XML
        try:
            sections = root.find('.//{http://www.elsevier.com/xml/common/dtd}sections')
            full_text = ""

            # Top level section
            for section in sections:
                # Markdown format
                header_top = self.convert_header('{http://www.elsevier.com/xml/common/dtd}', 1, section)
                full_text += header_top
                # Paragraph between section and secondary subsection
                # or paragraph with no subsection
                for para_top in section.findall('{http://www.elsevier.com/xml/common/dtd}para'):
                    para_text = self.process_paragraph(para_top)
                    full_text += para_text
                # Secondary level subsection
                for sec_section in section.findall('{http://www.elsevier.com/xml/common/dtd}section'):
                    header_sec = self.convert_header('{http://www.elsevier.com/xml/common/dtd}', 2, sec_section)
                    full_text += header_sec
                    for para_sec in sec_section.findall('{http://www.elsevier.com/xml/common/dtd}para'):
                        para_text = self.process_paragraph(para_sec)
                        full_text += para_text
                    # Tertiary level subsection
                    for ter_section in sec_section.findall('{http://www.elsevier.com/xml/common/dtd}section'):
                        header_ter = self.convert_header('{http://www.elsevier.com/xml/common/dtd}', 3, ter_section)
                        full_text += header_ter
                        for para_ter in ter_section.findall('{http://www.elsevier.com/xml/common/dtd}para'):
                            para_text = self.process_paragraph(para_ter)
                            full_text += para_text
                        # Quaternary level subsection
                        for qua_section in ter_section.findall('{http://www.elsevier.com/xml/common/dtd}section'):
                            header_qua = self.convert_header('{http://www.elsevier.com/xml/common/dtd}', 4, qua_section)
                            full_text += header_qua
                            for para_qua in qua_section.iter('{http://www.elsevier.com/xml/common/dtd}para'):
                                para_text = self.process_paragraph(para_qua)
                                full_text += para_text

            loader.add_value("full_text", full_text)
            loader.add_value("full_text_type", "markdown")
        except Exception as e:
            pass

        # Extract full text from raw text
        try:

            # Retrieve the raw text via regex
            raw_text = re.search(r'<xocs:rawtext.*?>(.*?)</xocs:rawtext>', str(response.body)).group()

            # Load the raw text to the loader
            loader.add_value("full_text", raw_text)
            if raw_text is not None:
                loader.add_value("full_text_type", "plain text")
        except Exception as e:
            pass

        # Extract tables
        try:
            # Iterate through each table
            for table in root.findall(".//{http://www.elsevier.com/xml/common/dtd}table"):
                # Add the table label and caption
                label = table.find('.//{http://www.elsevier.com/xml/common/dtd}label')
                markdown_table = f"{ET.tostring(label, encoding='unicode').strip()}\n\n"
                caption = table.find(
                    './/{http://www.elsevier.com/xml/common/dtd}caption/{http://www.elsevier.com/xml/common/dtd}simple-para')
                caption = re.sub(r'\n', '', ET.tostring(caption, encoding='unicode'))
                caption = re.sub(r'\s+', ' ', caption).strip()
                markdown_table += f"{caption}\n\n"
                # Define the Markdown table header
                markdown_table += "|"
                # Extract row entries and values
                for row in table.findall(".//{http://www.elsevier.com/xml/common/cals/dtd}row"):
                    for entry in row.findall(".//{http://www.elsevier.com/xml/common/dtd}entry"):
                        # Remove tags and replace HTML entities
                        value = ET.tostring(entry, encoding="unicode").strip() if entry.text else ""
                        # Remove \n
                        value = value.replace("\n", "")
                        # Replace \s+
                        value = re.sub(r"\s+", " ", value).strip()
                        # Add the value to the Markdown table
                        markdown_table += f"{value}|"
                    # Add a line break after each row
                    markdown_table += "\n|"

                # Print the Markdown table for each table
                markdown_table = markdown_table.rstrip("|")
                loader.add_value("table", markdown_table)
        except Exception as e:
            pass

        # Extract appendices(SI) from links in objects class
        # SI type = "APPLICATION" mimetype="application/word" or "application/pdf"
        try:
            count_si = 0
            si = root.findall('.//{http://www.elsevier.com/xml/svapi/article/dtd}object[@type="APPLICATION"]')
            si_objects = [obj for obj in si if
                          (obj.get("mimetype") == "application/word"
                           or obj.get("mimetype") == "application/pdf")
                          is True]
            # Total number of SI
            total_si = len(si_objects)
            # Check if it is necessary to download SI
            if total_si == 0:
                yield loader.load_item()
            else:
                # Iterate through each SI
                for si_object in si_objects:
                    # Remove quotation marks and text after "?"
                    url = re.sub(r'"|\?.*$', '', si_object.text)
                    print(url)
                    # Add the API key to the header
                    url = url + '?APIKey=' + self.api_key
                    count_si += 1
                    yield scrapy.Request(url=url, callback=self.parse_si, dont_filter=True,
                                         meta={"loader": loader, "doi": response.meta["doi"], "n": count_si,
                                               "total": total_si})
        except Exception as e:
            pass

    # Parse supplementary information(SI)
    @staticmethod
    def parse_si(response):
        loader = response.meta["loader"]
        doi = response.meta["doi"].replace("/", "_")
        n = response.meta["n"]
        # Get file format from url
        # Remove text after "?"
        url = re.sub(r'\?.*$', '', response.url)
        form = url.split(".")[-1]

        # Makedirs and save files
        if not os.path.exists(f'./data/si/{doi}'):
            os.makedirs(f'./data/si/{doi}')
        # Save files
        try:
            if response.status == 200:
                file_name = f'supplementary_meterial_{n}.{form}'
                path = f'./data/si/{doi}/{file_name}'
                print(path)
                loader.add_value("si", path)
                # with open(path, "wb") as f:
                #     f.write(response.body)
        except Exception as e:
            print(e)
            pass
        # Check if the amount of collected "si" is equal to the total number of SI
        if len(loader.get_collected_values("si")) == response.meta["total"]:
            yield loader.load_item()
        else:
            pass

    @staticmethod
    def convert_header(ns, level, element):
        """
        Convert headers from XML element to markdown format.

        Args:
            ns(str): namespace
            level(int): level of header
            element(xml.etree.ElementTree.Element): XML element

        Returns:
            str: header in markdown
        """
        # Get the header label
        label = element.find(f'.//{ns}label')
        # Get the header title
        section_title = element.find(f'.//{ns}section-title')
        # Return header as markdown
        return f"{'#' * level} {ET.tostring(label, encoding='unicode').strip()} {ET.tostring(section_title, encoding='unicode').strip()}\n\n"

    @staticmethod
    def process_paragraph(element):
        """
        Process paragraphs in XML format to plain text.

        Args:
            element(xml.etree.ElementTree.Element): XML element of paragraph

        Returns:
            str: plain text of paragraph
        """
        para_text = ET.tostring(element, encoding="unicode")
        # Remove \n, \t and multiple \s
        para_text = re.sub(r'\n', '', para_text)
        para_text = re.sub(r'\t', '', para_text)
        para_text = re.sub(r'\s+', ' ', para_text).strip()
        # Convert the last </ns0:para> to \n\n
        para_text = re.sub(r'</ns0:para>$', '\n\n', para_text)

        return para_text

    def generate_doi_urls(self, doi_list_file):
        with open(doi_list_file, 'r') as f:
            reader = csv.reader(f)
            self.doi_list = [row[0] for row in reader]

        base_url = "https://api.elsevier.com/content/article/doi/"
        # Create a list of dict. Format as [{"doi":"", "url":""}].
        doi_urls = [{"doi": doi, "url": base_url + doi} for doi in self.doi_list]

        return doi_urls
