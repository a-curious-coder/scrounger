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

def extract_job_page_url(urls: List[str], blacklist=[]) -> Optional[str]:
    """Use OpenAI to analyze the URLs and find the most likely job listings page."""
    logger.info("🤖 Analyzing URLs to find job listings page")
    prompt = f"Given the following list of URLs, give me the one URL that is most likely to contain the company's job listings. You must only respond with the URL, nothing else. The URL must not be an exact match to any urls in the following blacklist although if it's similar, that is allowed.: [{blacklist}\nIf you are not sure, simply say \"None\":\n\n" + "\n".join(urls)
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    job_page_url = response.choices[0].message.content.strip()
    if job_page_url.lower() != 'none':
        logger.info(f"✅ Identified job listings page: {job_page_url}")
        return job_page_url
    else:
        logger.warning("❌ Could not identify job listings page")
        return None

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
