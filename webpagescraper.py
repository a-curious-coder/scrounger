import time
import random
import logging
from typing import Optional
from urllib.parse import urlparse

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from selenium.webdriver.common.action_chains import ActionChains

class WebPageScraper:
    def __init__(self, headless: bool = True):
        self.logger = self._setup_logger()
        self.options = self._setup_chrome_options(headless)
        self.driver = None

    def _setup_logger(self):
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger(__name__)

    def _setup_chrome_options(self, headless: bool) -> Options:
        options = Options()
        if headless:
            options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--window-size=1920,1080")
        options.add_argument(f'user-agent={UserAgent().random}')
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        return options

    def _init_driver(self):
        if not self.driver:
            self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=self.options)

    def _quit_driver(self):
        if self.driver:
            self.driver.quit()
            self.driver = None

    @staticmethod
    def _random_delay(min_seconds: float = 1, max_seconds: float = 5):
        time.sleep(random.uniform(min_seconds, max_seconds))

    def _human_like_scroll(self):
        total_height = self.driver.execute_script("return document.body.scrollHeight")
        viewport_height = self.driver.execute_script("return window.innerHeight")
        current_position = 0
        while current_position < total_height:
            scroll_amount = random.randint(100, viewport_height)
            self.driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
            current_position += scroll_amount
            self._random_delay(0.5, 2)

    def _random_mouse_movement(self):
        action = ActionChains(self.driver)
        for _ in range(random.randint(1, 5)):
            x = random.randint(0, self.driver.execute_script("return window.innerWidth;"))
            y = random.randint(0, self.driver.execute_script("return window.innerHeight;"))
            action.move_by_offset(x, y)
        action.perform()

    def get_html(self, url: str, max_retries: int = 5) -> Optional[str]:
        self._init_driver()
        try:
            return self._navigate_and_get_html(url, url, max_retries)
        finally:
            self._quit_driver()

    def _navigate_and_get_html(self, original_url: str, current_url: str, retries_left: int) -> Optional[str]:
        if retries_left == 0:
            self.logger.warning(f"Max retries reached. Proceeding with the last accessed URL: {current_url}")
            return self._get_html_content(current_url)

        self.driver.get(current_url)
        self._random_delay(2, 5)

        if self.driver.current_url != original_url:
            self.logger.info(f"Redirected to {self.driver.current_url}. Attempts left: {retries_left-1}")
            return self._navigate_and_get_html(original_url, original_url, retries_left - 1)
        else:
            return self._get_html_content(original_url)

    def _get_html_content(self, url: str) -> Optional[str]:
        try:
            WebDriverWait(self.driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            self._human_like_scroll()
            self._random_mouse_movement()
            self._random_delay(3, 7)
            return self.driver.page_source
        except Exception as e:
            self.logger.error(f"Error while getting HTML content: {e}")
            return None

    @staticmethod
    def save_html_to_file(html_content: str, file_name: str):
        with open(file_name, 'w', encoding='utf-8') as file:
            file.write(html_content)

def main():
    url = "https://www.futurlab.co.uk/careers#vacancies"
    scraper = WebPageScraper(headless=True)
    html_content = scraper.get_html(url)

    if html_content:
        soup = BeautifulSoup(html_content, 'html.parser')
        pretty_html = soup.prettify()
        # Get the base URL (domain) of the first URL in the list
        base_url = urlparse(url).netloc
        
        # Remove 'www.' if present
        base_url = base_url.replace('www.', '').replace('.co.uk', '').replace('.com', '')
        scraper.save_html_to_file(pretty_html, f'{base_url}_content.html')
        scraper.logger.info("HTML content saved to page_content.html")
    else:
        scraper.logger.error("Failed to retrieve HTML content")

if __name__ == "__main__":
    main()