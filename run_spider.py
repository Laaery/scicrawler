"""
This is the entry point to run a spider.
"""
import argparse
import os
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from scrapy.utils.log import configure_logging
import logging
import time



def main():
    parser = argparse.ArgumentParser(description="Run a Scrapy spider with DOI list input.")
    parser.add_argument("--spider", type=str, required=True, help="Name of the spider to run")
    parser.add_argument("--domain", type=str, required=True, help="Domain name to pass to the spider")
    parser.add_argument("--doi_file", type=str, required=True, help="Path to the DOI list CSV file")
    parser.add_argument("--log_dir", type=str, default="./log", help="Directory to store log files")
    parser.add_argument("--publisher", type=str, help="Publisher name for the spider")
    parser.add_argument("--api_key", type=str, help="API key for the spider")
    parser.add_argument("--mongo_uri", type=str, default="mongodb://localhost:27017", help="MongoDB URI for the spider")
    parser.add_argument("--mongo_db", type=str, help="MongoDB database name for the spider")
    parser.add_argument("--mongo_collection", type=str, default="test", help="MongoDB collection name for the spider")

    args = parser.parse_args()

    # Ensure log directory exists
    os.makedirs(args.log_dir, exist_ok=True)

    # Set up logging
    log_path = os.path.join(args.log_dir, f"log_{args.spider}_{time.strftime('%Y-%m-%d')}.log")
    logging.basicConfig(
        filename=log_path,
        encoding="utf-8",
        format="%(asctime)s %(filename)s [line:%(lineno)d] %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO
    )

    logging.info(f"Starting spider '{args.spider}' on domain '{args.domain}' with DOI file '{args.doi_file}'")

    # Start crawler process with project settings
    settings = get_project_settings()
    # API key
    settings.set(f"{args.publisher.upper()}_API_KEY", args.api_key, priority="spider")
    # MongoDB settings
    if not args.mongo_db:
        args.mongo_db = "sci_crawler"
    if not args.mongo_collection:
        args.mongo_collection = args.publisher.lower()
    settings.set("MONGO_URI", args.mongo_uri, priority="spider")
    settings.set("MONGO_DATABASE", args.mongo_db, priority="spider")
    settings.set("MONGO_COLLECTION", args.mongo_collection, priority="spider")
    process = CrawlerProcess(settings)

    # Pass arguments to spider via `crawl` keyword args
    process.crawl(
        args.spider,
        domain=args.domain,
        doi_list_file=args.doi_file
    )

    process.start()


if __name__ == "__main__":
    main()
