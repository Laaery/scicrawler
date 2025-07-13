# Define your item pipelines here
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
import pymongo


class SciCrawlerPipeline:
    def process_item(self, item, spider):
        return item


class MongoPipeline:

    def __init__(self, mongo_uri, mongo_db, mongo_col):
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db
        self.mongo_col = mongo_col

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            mongo_uri=crawler.settings.get("MONGO_URI"),
            mongo_db=crawler.settings.get("MONGO_DATABASE"),
            mongo_col=crawler.settings.get("MONGO_COLLECTION"),
        )

    def open_spider(self, spider):
        self.client = pymongo.MongoClient(self.mongo_uri)
        self.db = self.client[self.mongo_db]

    def close_spider(self, spider):
        self.client.close()

    def process_item(self, item, spider):
        self.db[self.mongo_col].insert_one(ItemAdapter(item).asdict())

        # # Try to update the item if it exists, otherwise pass. You can replace whatever field you want to update.
        # try:
        #     self.db[self.mongo_col].update_one({"doi": item["doi"]},
        #                                        {"$set": {"si": item["si"]}},
        #                                        upsert=False)
        # except Exception as e:
        #     pass
        return item
