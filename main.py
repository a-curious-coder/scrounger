import csv
import argparse
from typing import List, Optional
import openai
from urllib.parse import urlparse, urljoin
import requests
import logging
import os
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import hashlib
import time
import json
from jobcrawler import JobCrawler
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

JINA_API_KEY = os.environ.get('JINAAI_API_KEY')
JINA_READ_URL = "https://r.jina.ai/"

# Set your OpenAI API key
openai.api_key = os.environ.get("OPENAI_API_KEY")

if openai.api_key is None:
    logging.warning("No OpenAI API key provided...")
    exit(0)


def process_company(homepage_url: str, output_file: str):
    """Process a company to find and extract job listings."""
    logger.info(f"🏢 Attempting to scrape job ads from: {homepage_url}")

    # Create a folder called "Job Ads" if it doesn't exist
    careers_folder = "Job Ads"
    os.makedirs(careers_folder, exist_ok=True)

    # Generate a filename based on the homepage URL
    crawler = JobCrawler(homepage_url)

    if crawler.find_job_page():
        crawler.save_job_page_url(careers_file)
        crawler.process_job_listings(output_file)
        logger.info("✨ Job extraction process completed")
    else:
        logger.error("Failed to find job listings. Exiting.")

def main():
    parser = argparse.ArgumentParser(description="Extract job listings for a company")
    parser.add_argument("homepage_url", help="URL of the company's homepage")
    parser.add_argument("--output", default="job_listings.csv", help="Output CSV file name")
    args = parser.parse_args()

    process_company(args.homepage_url, args.output)

if __name__ == "__main__":
    main()
