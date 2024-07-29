import csv
import argparse
from dataclasses import dataclass
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
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

JINA_API_KEY = os.environ.get('JINAAI_API_KEY')
JINA_READ_URL = "https://r.jina.ai/"

# Set your OpenAI API key
openai.api_key = os.environ.get("OPENAI_API_KEY")

if openai.api_key is None:
    logging.warning("No OpenAI API key provided...")
    exit(0)

@dataclass
class JobAd:
    """Data class to store job advertisement information."""
    url: str
    title: str
    description: str
    company: str
    location: Optional[str] = None
    salary: Optional[str] = None

def get_html_content(url: str) -> str:
    """Get the HTML content of a webpage using requests, caching the result."""
    logger.info(f"🌐 Fetching HTML content for URL: {url}")
    
    # Create a folder to store HTML files if it doesn't exist
    cache_folder = "HTML_Cache"
    os.makedirs(cache_folder, exist_ok=True)
    
    # Create a unique filename based on the URL
    url_hash = hashlib.md5(url.encode()).hexdigest()
    file_path = os.path.join(cache_folder, f"{url_hash}.html")
    
    # Check if the file already exists and is not too old (e.g., less than a day old)
    if os.path.exists(file_path) and (time.time() - os.path.getmtime(file_path) < 86400):
        logger.info(f"📂 Reading HTML content from cache: {file_path}")
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        logger.debug(f"📄 Read cached HTML content (length: {len(content)} characters)")
        return content
    
    # If file doesn't exist or is too old, fetch the content and save it
    logger.info(f"🔍 Fetching fresh HTML content for URL: {url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()  # Raise an exception for bad status codes
        content = response.text
        
        # Save the content to a file
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(content)
        logger.info(f"💾 Saved HTML content to cache: {file_path}")
        
        logger.debug(f"📄 Received HTML content (length: {len(content)} characters)")
        return content
    
    except requests.RequestException as e:
        logger.error(f"❌ Failed to fetch HTML content for {url}: {str(e)}")
        return ""

def extract_urls_from_html(html_content: str, base_url: str) -> List[str]:
    """Extract all unique, valid URLs from the HTML content."""
    logger = logging.getLogger(__name__)
    logger.info(f"🔍 Extracting URLs from HTML content (base URL: {base_url})")
    
    soup = BeautifulSoup(html_content, 'html.parser')
    urls = set()
    
    for tag in soup.find_all(['a', 'link']):
        href = tag.get('href') or tag.get('src')
        if href:
            full_url = urljoin(base_url, href)
            parsed = urlparse(full_url)
            if parsed.scheme in ('http', 'https') and parsed.netloc:
                urls.add(full_url)
    
    unique_urls = list(urls)
    logger.debug(f"📋 Extracted {len(unique_urls)} unique URLs")
    return unique_urls

def extract_job_page_url(urls: List[str], blacklist=[]) -> Optional[str]:
    """Use OpenAI to analyze the URLs and find the most likely job listings page."""
    logger.info("🤖 Analyzing URLs to find job listings page")
    prompt = f"Given the following list of URLs, give me only one URL that is most likely to contain the company's job listings. It must not be in the following blacklist: [{blacklist}\nIf you are not sure, simple say \"None\":\n\n" + "\n".join(urls)
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


def verify_job_listing(url):
    """
    Verify if a given URL represents a job listing.
    
    Args:
    url (str): The URL to verify

    Returns:
    bool: True if the URL likely represents a job listing, False otherwise
    """
    try:
        # Fetch the webpage content
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Check for common job listing indicators in the title
        title = soup.title.string.lower() if soup.title else ""
        title_indicators = ['job', 'career', 'position', 'opening', 'vacancy', 'hire', 'employment']
        if any(indicator in title for indicator in title_indicators):
            return True
        
        # Check for common job listing keywords in the page content
        content = soup.get_text().lower()
        content_indicators = [
            'job description', 'responsibilities', 'qualifications', 
            'requirements', 'apply now', 'submit your resume', 
            'work experience', 'salary', 'benefits'
        ]
        if any(indicator in content for indicator in content_indicators):
            return True
        
        # Check for structured job posting data
        job_schema = soup.find('script', type='application/ld+json')
        if job_schema:
            if '"@type": "JobPosting"' in job_schema.string:
                return True
        
        # Check for common job listing URL patterns
        url_patterns = ['/jobs/', '/careers/', '/job-', '/career-', 'job_id=', 'jobid=']
        if any(pattern in url.lower() for pattern in url_patterns):
            return True
        
        # If none of the above checks pass, it's likely not a job listing
        return False
    
    except requests.RequestException:
        # Handle any request errors
        print(f"Error fetching URL: {url}")
        return False


def extract_job_listings(potential_job_urls: List[str], blacklist=[]) -> List[str]:
    """Filter and extract valid job listing URLs from a list of potential URLs using ChatGPT."""
    logger.info("🔍 Extracting job listing URLs")
    
    prompt = f"""
    From the following list of URLs, identify and return only the valid urls that represent job listings themselves. The urls should not be in this blacklist: [{blacklist}]
    Return the URLs as a JSON array of strings.
    Only include URLs that are likely to lead directly to job postings or job application pages.
    Do not include any explanation or additional text.
    If you do not find any valid job listing urls; simple return a value saying "none" within the JSON array.

    URLs:
    {json.dumps(potential_job_urls, indent=2)}
    """
    
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,  # Set to 0 for more consistent output
        )
        
        # Parse the JSON response
        job_urls = json.loads(response.choices[0].message.content.strip())
        
        # Ensure the result is a list of strings
        if not isinstance(job_urls, list) or not all(isinstance(url, str) for url in job_urls):
            raise ValueError("ChatGPT did not return a valid list of URLs")
        
        logger.debug(f"📋 Extracted {len(job_urls)} job listing URLs out of {len(potential_job_urls)} potential URLs")
        final = []
        # verify job urls:
        for url in job_urls.copy:
            if is_job_listing_url(url):
                final.append(url)
        return final
    
    except (json.JSONDecodeError, ValueError, openai.OpenAIError) as e:
        logger.error(f"❌ Error extracting job URLs: {str(e)}")
        return []

def extract_data_from_job_listing(html_content: str) -> dict:
    """Use OpenAI to analyze the job listing HTML and extract job information."""
    logger.info("🤖 Analyzing job listing HTML")
    prompt = f"""
    Analyze the following HTML content and extract job information. 
    Return the information in CSV format using the following template:
    url,title,description,company,location,salary
    
    If you cannot find information for a field, leave it empty.
    
    HTML content:
    {html_content}
    """
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    csv_data = response.choices[0].message.content.strip().split('\n')[1]  # Skip header
    job_info = dict(zip(['url', 'title', 'description', 'company', 'location', 'salary'], csv_data.split(',')))
    logger.debug(f"📊 Extracted job information: {job_info}")
    return job_info


def write_to_csv(job_ad: JobAd, filename: str):
    """Write a job advertisement to a CSV file if it's not already present."""
    logger.info(f"📝 Writing job ad to CSV: {filename}")
    fieldnames = ['url', 'title', 'description', 'company', 'location', 'salary']
    
    try:
        with open(filename, 'r') as f:
            existing_urls = [row['url'] for row in csv.DictReader(f)]
    except FileNotFoundError:
        existing_urls = []
    
    if job_ad.url not in existing_urls:
        with open(filename, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if f.tell() == 0:
                writer.writeheader()
            writer.writerow(job_ad.__dict__)
        logger.debug(f"✅ Job ad written to CSV: {job_ad.url}")
    else:
        logger.debug(f"⏭️ Job ad already exists in CSV, skipping: {job_ad.url}")


def save_job_page_url(company_name, job_page_url):
    folder_name = "Company Careers"
    os.makedirs(folder_name, exist_ok=True)
    
    file_path = os.path.join(folder_name, f"{company_name}_career_page.txt")
    with open(file_path, 'w') as f:
        f.write(job_page_url)
    
    logger.info(f"✅ Saved job page URL for {company_name}")

class JobCrawler:
    def __init__(self, homepage_url):
        self.homepage_url = homepage_url
        self.crawl_url = homepage_url
        self.job_page_url = None
        self.job_urls = []

    def find_job_page(self):
        visited_urls = []
        contains_job_listings = False
        while not contains_job_listings:
            crawl_html = get_html_content(self.crawl_url)
            urls = extract_urls_from_html(crawl_html, self.crawl_url)
            self.job_page_url = extract_job_page_url(urls, blacklist=visited_urls)
            self.job_urls = extract_job_listings(urls, blacklist=visited_urls)

            if self.job_urls[0].lower() != "none":
                contains_job_listings = True
            elif self.job_page_url:
                self.crawl_url = self.job_page_url
            else:
                logger.error(f"❌ Cannot find job listings page for {self.homepage_url}")
                return False
        return True

    def save_job_page_url(self, careers_file):
        with open(careers_file, 'w') as f:
            f.write(self.job_page_url)
        logger.info(f"💾 Saved job page URL to file: {careers_file}")

    def process_job_listings(self, output_file):
        for job_url in self.job_urls:
            logger.info(f"📄 Processing job listing: {job_url}")
            job_html = get_html_content(job_url)
            job_info = extract_data_from_job_listing(job_html)
            job_ad = JobAd(
                url=job_url,
                title=job_info['title'],
                description=job_info['description'],
                company=urlparse(self.homepage_url).netloc,
                location=job_info['location'],
                salary=job_info['salary']
            )
            write_to_csv(job_ad, output_file)

def process_company(homepage_url: str, output_file: str):
    """Process a company to find and extract job listings."""
    logger.info(f"🏢 Processing company: {homepage_url}")
    
    # Create a folder called "Company Careers" if it doesn't exist
    careers_folder = "Company Careers"
    os.makedirs(careers_folder, exist_ok=True)
    
    # Generate a filename based on the homepage URL
    company_name = homepage_url.split("//")[-1].split(".")[0]
    careers_file = os.path.join(careers_folder, f"{company_name}_careers.txt")
    
    crawler = JobCrawler(homepage_url)
    
    if crawler.find_job_page():
        crawler.save_job_page_url(careers_file)
        crawler.process_job_listings(output_file)
    else:
        logger.error("Failed to find job listings. Exiting.")

def main():
    parser = argparse.ArgumentParser(description="Extract job listings for a company")
    parser.add_argument("homepage_url", help="URL of the company's homepage")
    parser.add_argument("--output", default="job_listings.csv", help="Output CSV file name")
    args = parser.parse_args()

    logger.info(f"🚀 Starting job extraction process for {args.homepage_url}")
    process_company(args.homepage_url, args.output)
    logger.info("✨ Job extraction process completed")

if __name__ == "__main__":
    main()

# Search google and extract the url for the company's homepage
# Using jina read; get the html for the hompage
# using openai, analyse the html for the homepage and find the url for the webpage that would most likely have the company's job listings
# If openai doesn't find the url for the page with job listings, explicitly state you cannot find it and return.
# if openai does find the url, only respond with the URL only
# Use jinsa read using the job listings web page url. 
# Extract the urls for the job listings;
# For each job ad
# Analyse the job listing html with jinsa read
# Extract the job info; like job url, job title, job description, etc. Use Openai for this
# Explicitly state openai to return the information in a csv format using a predetermined template we provide it with; if it cannot find information, don't write anything for that.
# Create a data class to store job ad info;
# Create a job ad object and populate with info (if there is info)
# Write the job ad to a csv if it's not within the csv file.
# Loop for every job.
