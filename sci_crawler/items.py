# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy
from itemloaders.processors import MapCompose, Join
from w3lib.html import remove_tags
from w3lib.html import replace_entities
import re


class Metadata(scrapy.Item):

    doi = scrapy.Field(
        input_processor=MapCompose(remove_tags, replace_entities, str.strip),
        output_processor=Join(),
    )
    title = scrapy.Field(
        input_processor=MapCompose(remove_tags, replace_entities,
                                   lambda x: re.sub(r'\n', ' ', x, re.S),
                                   lambda x: re.sub(r'\s+', ' ', x, re.S),
                                   str.strip),
        output_processor=Join(),
    )
    abstract = scrapy.Field(
        input_processor=MapCompose(remove_tags,
                                   replace_entities,
                                   lambda x: re.sub(r'\n', ' ', x, re.S),
                                   lambda x: re.sub(r'\s+', ' ', x, re.S),
                                   str.strip),
        output_processor=Join(),
    )
    full_text = scrapy.Field(
        input_processor=MapCompose(lambda x: re.sub(r'</p>', '\n\n', x, re.S),
                                   remove_tags,
                                   replace_entities),
        output_processor=Join(),
    )
    full_text_type = scrapy.Field(output_processor=Join())
    table = scrapy.Field(input_processor=MapCompose(remove_tags, replace_entities, str.strip))
    si = scrapy.Field()