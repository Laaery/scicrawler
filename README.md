# SciCrawler⛏
## Overview
A text crawling tool modified on Scrapy for scientific community, especially chemistry, material science, biology and environmental science.
## Prerequisites
1. Python 3.8 or higher
2. MongoDB server (local or remote)
3. API keys for publisher platforms (where required)
## Installation
```bash
git clone https://github.com/Laaery/scicrawler.git
cd scicrawler
pip install -r requirements.txt
```
## Usage
1. Prepare a list of DOIs to scrape, categorized by publishers, in independent csv files within `doi_list/` directory.
2. Establish a MongoDB database to store the scraped data.
3. Run the `run_spider.py` script. For example, to download data via Elsevier API, use the following command:
```bash
python run_spider.py \
    --spider spider_elsevier_api \
    --domain api.elsevier.com \
    --doi_file ./doi_list/your_doi.csv \
    --publisher Elsevier \
    --api_key YOUR_API_KEY
```
## Legal and Ethical Considerations
Important: Users are solely responsible for complying with:
- Publisher terms of service
- Copyright laws
- API rate limits
- Robots.txt directives

**Disclaimer**: This tool is provided for research purposes only. The developers are not responsible for any misuse or violations of publisher policies committed by users.
