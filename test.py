from typing import List
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import openai
import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# logger = logging.getLogger(__name__)

# Set up your OpenAI API key
openai.api_key = os.environ.get("OPENAI_API_KEY")

def extract_urls_from_html(html_content: str, base_url: str) -> List[str]:
    """Extract all unique, valid URLs from the HTML content."""
    # logging.info(f"🔍 Extracting URLs from HTML content (base URL: {base_url})")
    
    soup = BeautifulSoup(html_content, 'html.parser')
    urls = set()
    
    for tag in soup.find_all('a', href=True):
        href = tag.get('href')
        if href:
            full_url = urljoin(base_url, href)
            parsed = urlparse(full_url)
            if parsed.scheme in ('http', 'https') and parsed.netloc:
                urls.add(full_url)
    
    # Filter URLs to only include those likely to be job-related
    job_keywords = ['job', 'career', 'employment', 'vacancy', 'position', 'opportunity', 'hiring']
    filtered_urls = [url for url in urls if any(keyword in url.lower() for keyword in job_keywords)]
    
    logging.info(f"📋 Extracted {len(filtered_urls)} URLs")
    return filtered_urls

def get_urls_from_page(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        links = soup.find_all('a', href=True)
        return [urljoin(url, link['href']) for link in links]
    except requests.RequestException:
        return []

def find_most_likely_job_page(urls, blacklist=[]):
    prompt = f"""
    Given the following list of URLs, identify which URL is most likely to contain job listings:
    {', '.join(urls)}
    Ignore urls listed here: [{', '.join(blacklist)}]
    Respond with only the URL that is most likely to contain job listings.
    """
    
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=100,
        n=1,
        stop=None,
        temperature=0.5,
    )
    
    answer = response.choices[0].message.content.strip()
    logging.info(f"Most likely job page URL: {answer}")
    return answer

def is_job_listings_page(url, urls):
    prompt = f"""
    Analyze the following list of urls and determine if the list contains actual job listing urls; not the url to the webpage that will contain them.
    This page: {url}
    The urls on this page: {', '.join(urls)}
    
    Respond with 'Yes' if this page contains job listings, or 'No' if it's doesn't.
    """
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1,
        n=1,
        stop=None,
        temperature=0.5,
    )
    
    answer = response.choices[0].message.content.strip().lower()
    if answer == 'yes':
        prompt = f"""
        Considering this list of urls: {', '.join(urls)}
        
        List all urls that represent job listings. This list must be formatted as a single line of comma separated values.
        """
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1,
            n=1,
            stop=None,
            temperature=0.5,
        )
        print(*response.choices[0].content, "\n")
        return True
    return False

def verify_job_listings_page(url):
    try:
        response = requests.get(url)
        page_content = response.text
        potential_urls = extract_urls_from_html(page_content, url)
        
        return is_job_listings_page(url, potential_urls)
    except requests.RequestException:
        return False
    
def find_job_listings(start_url, max_attempts=10):
    visited_urls = set()
    urls_to_check = [start_url]
    
    for _ in range(max_attempts):
        if not urls_to_check:
            break
        
        current_url = urls_to_check.pop(0)
        
        if current_url in visited_urls:
            continue
        
        visited_urls.add(current_url)
        
        try:
            response = requests.get(current_url)
            page_content = response.text
            potential_urls = extract_urls_from_html(page_content, start_url)
            
            most_likely_url = find_most_likely_job_page(potential_urls, visited_urls)
            
            if most_likely_url and verify_job_listings_page(most_likely_url):
                return most_likely_url
            
            urls_to_check.extend([url for url in potential_urls if url not in visited_urls])
        
        except requests.RequestException:
            continue
    
    return None

# Usage
start_url = "https://www.marksandspencer.com/"  # Replace with the website you want to crawl
job_listings_url = find_job_listings(start_url)

if job_listings_url:
    print(f"Job listings found at: {job_listings_url}")
    file_name = job_listings_url.split(".")[1]
    print(f"saving as {file_name}.txt")
    with open(f"{file_name}.txt", "w", encoding="utf-8") as f:
        f.writelines(job_listings_url)
        f.close()
    
else:
    print("No job listings page found within the maximum attempts.")