import re
import os
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import openai
import requests
from dotenv import load_dotenv

load_dotenv()

class URLValidator:
    def __init__(self):
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OpenAI API key not found in environment variables")
        openai.api_key = self.openai_api_key

    def validate_career_page(self, url, html_content):
        """Validate if the given URL is indeed a career page by analyzing its HTML content."""
        # Extract key elements from the HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        title = soup.title.string if soup.title else ""
        headers = [h.text for h in soup.find_all(['h1', 'h2', 'h3'])]
        paragraphs = [p.text for p in soup.find_all('p')]
        
        # Prepare the content for analysis
        content_summary = f"""
        URL: {url}
        Title: {title}
        Headers: {' | '.join(headers[:5])}  # Limit to first 5 headers
        Paragraphs: {' '.join(paragraphs[:3])}  # Limit to first 3 paragraphs
        """

        prompt = f"""
        Analyze the following webpage content to determine if it's a career/jobs page:

        {content_summary}

        Respond with only one of these:
        VALID_CAREER_PAGE
        INVALID_CAREER_PAGE

        Explanation: [Your reasoning here]
        """

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that validates career pages."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.3,
        )

        result = response.choices[0].message['content'].strip()
        is_valid = result.startswith("VALID_CAREER_PAGE")
        explanation = result.split("Explanation:")[1].strip() if "Explanation:" in result else ""
        
        return is_valid, explanation

    def validate_job_listings(self, urls):
        """Validate if the given URLs are indeed job listings."""
        url_list = "\n".join(urls[:20])  # Limit to 20 URLs to avoid token limit
        prompt = f"""
        Analyze the following URLs to confirm if they are job listings:

        {url_list}

        Respond with:
        VALID_JOB_LISTINGS
        <url1>
        <url2>
        ...

        Or if no valid job listings are found:
        NO_VALID_JOB_LISTINGS
        """

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that validates job listing URLs."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.3,
        )

        result = response.choices[0].message['content'].strip()
        if result.startswith("VALID_JOB_LISTINGS"):
            return self.extract_urls_from_text(result)
        return []

    @staticmethod
    def extract_urls_from_text(text):
        """Extract URLs from a given text."""
        url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+(?:/[^?\s]*)?(?:\?[^\s#]*)?(?:#[^\s]*)?'
        return re.findall(url_pattern, text)
