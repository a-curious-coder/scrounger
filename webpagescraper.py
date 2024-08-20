""" Gets the html from a web-page """
import os
import time
import requests
import logging
from urllib.parse import urlparse

class WebPageScraper:
    def __init__(self, cache_folder="HTML_Cache"):
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        self.cache_folder = cache_folder
        os.makedirs(self.cache_folder, exist_ok=True)

    def get_html(self, url: str) -> str:
        self.logger.info(f"Fetching HTML content for URL: {url}")
        file_name = self._get_file_name(url)
        file_path = os.path.join(self.cache_folder, file_name)

        if self._is_cache_valid(file_path):
            return self._read_from_cache(file_path)

        return self._fetch_and_save(url, file_path)

    def _get_file_name(self, url: str) -> str:
        base_name = urlparse(url).netloc.replace('www.', '') + '.html'
        return base_name

    def _is_cache_valid(self, file_path: str) -> bool:
        return os.path.exists(file_path) and (time.time() - os.path.getmtime(file_path) < 86400)

    def _read_from_cache(self, file_path: str) -> str:
        self.logger.info(f"Reading HTML content from cache: {file_path}")
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()

    def _fetch_and_save(self, url: str, file_path: str) -> str:
        self.logger.info(f"Fetching fresh HTML content for URL: {url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            content = response.text

            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(content)
            self.logger.info(f"Saved HTML content to: {file_path}")

            return content
        except requests.RequestException as e:
            self.logger.error(f"Failed to fetch HTML content for {url}: {str(e)}")
            return ""

def main():
    url = "https://www.futurlab.co.uk/careers#vacancies"
    scraper = WebPageScraper()
    html_content = scraper.get_html(url)

    if html_content:
        scraper.logger.info("HTML content retrieval successful.")
    else:
        scraper.logger.error("Failed to retrieve HTML content.")

if __name__ == "__main__":
    main()
