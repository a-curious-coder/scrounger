""" Given the html of a webpage, this should be able to extract urls and determine whether they're job listings."""
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import openai
import json
import re
import os
from dotenv import load_dotenv

load_dotenv()

class URLExtractor:
    def __init__(self, base_url):
        self.base_url = base_url
        openai.api_key = os.environ.get("OPENAI_API_KEY")

    def get_urls_from_string(self, text):
        # Updated regular expression pattern to match more complete URLs
        url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+(?:/[^?\s]*)?(?:\?[^\s#]*)?(?:#[^\s]*)?'

        # Find all matches of the pattern in the text
        urls = re.findall(url_pattern, text)

        return urls

    def get_urls_from_html_file(self, html_file):
        with open(html_file, 'r', encoding='utf-8') as file:
            soup = BeautifulSoup(file, 'html.parser')

        urls = []
        for a in soup.find_all('a', href=True):
            url = urljoin(self.base_url, a['href'])
            urls.append(url)
        urls = set(urls)
        urls = [url for url in urls if self.base_url in url]
        return urls

    def analyse_urls(self, urls):
        url_list = "\n".join(urls[:20])  # Limit to 20 URLs to avoid token limit
        prompt = f"""
        Analyze the following URLs to identify job listings or pages likely to lead to job listings:

        {url_list}

        Respond in only one of the following formats (these are in order of priority):
        1. If job listings are found:
        JOB_LISTINGS
        <url1>
        <url2>
        ...

        2. If no job listings are found, but career pages are identified:
        CAREER_PAGES
        <url1>
        <url2>
        ...

        3. If neither job listings nor career pages are found:
        NO_RESULTS

        Prioritize job listings over career pages. If job listings are found, do not include career pages.
        """

        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that analyzes URLs."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            n=1,
            stop=None,
            temperature=0.5,
        )


        return response.choices[0].message.content.strip().lower()

    def validate_urls(self, urls):
        prompt = f"""
        Analyze the following URLs to identify job listings:

        {urls}

        Respond in only one of the following formats according to the condition:

        1. If job listings are found:
        JOB_LISTINGS
        <url1>
        <url2>
        ...

        2. If neither job listings nor career pages are found:
        NO_RESULTS

        """

        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that analyzes URLs."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.3,
        )
        resp = response.choices[0].message.content.strip().lower()
        return resp

    def process_urls(self, html_file):
        urls = self.get_urls_from_html_file(html_file)

        # NOTE: This will dictate whether we have found
        # 1. A careers page url
        # 2. A careers page with job listing urls
        # 3. Nothing useful (meaning we should abandon)
        analysis = self.analyse_urls(urls).lower()

        if "job_listings" in analysis:
            # Extract urls from analysis string
            job_listing_urls = self.get_urls_from_string(analysis)
            # Evaluate URLs using OpenAI to determine if they are job listings
            analysis = self.validate_urls(job_listing_urls)
            try:
                if analysis == "NO_RESULTS":
                    print("No listings apparently")
                    exit(0)
                fin = self.get_urls_from_string(analysis)
                self.save_urls_to_file(fin)

            except json.JSONDecodeError:
                return "Error: Unable to parse the response from the AI model."
        else:
            return f"No direct job listings found. Analysis: {analysis}"

    def save_urls_to_file(self, urls):
        if not urls:
            print("No URLs to save.")
            return

        # Get the base URL (domain) of the first URL in the list
        base_url = urlparse(urls[0]).netloc

        # Remove 'www.' if present
        base_url = base_url.replace('www.', '')

        # Create a filename
        filename = f"{base_url}_urls.txt"

        # Ensure the filename is valid
        filename = "".join(c for c in filename if c.isalnum() or c in ('_', '.', '-'))

        # Write URLs to the file
        with open(filename, 'w') as file:
            for url in urls:
                file.write(url + '\n')

        print(f"URLs have been saved to {filename}")

# Usage example
extractor = URLExtractor('https://www.futurlab.co.uk')
result = extractor.process_urls('HTMLCache/futurlab.html')
print(result)
