from webpagescraper import WebPageScraper
from urlextractor import URLExtractor
from urllib.parse import urljoin, urlparse
from jobad import JobAd
import logging
import csv

logger = logging.getLogger(__name__)

class JobCrawler:
    def __init__(self, homepage_url):
        self.homepage_url = homepage_url
        self.crawl_url = ""
        self.job_page_url = ""
        self.job_urls = []
        self.webpagescraper = WebPageScraper()
        self.urlextractor = URLExtractor(homepage_url)

    def find_job_page(self):
        visited_urls = []
        contains_job_listings = False # Verifies it's a careers page
        company_domain = self.crawl_url.strip("https://")
        while not contains_job_listings:
            crawl_html = self.webscraper.get_html_content(self.crawl_url)
            urls = self.urlextractor.get_urls_from_html_file(crawl_html, self.homepage_url)
            self.job_page_url = extract_job_page_url(urls, blacklist=visited_urls)
            if self.job_page_url is None or self.job_page_url in visited_urls:
                self.job_page_url = None
                # Attempt to find careers page via google
                potential_career_urls = [
                    f"https://{company_domain}/jobs",
                    f"https://{company_domain}/careers",
                    f"https://{company_domain}/work-with-us",
                    f"https://{company_domain}/join-our-team",
                    f"https://careers.{company_domain}",
                ]

                for url in potential_career_urls:
                    if url not in visited_urls:
                        career_page_html = self.webscraper.get_html_content(url)
                        if career_page_html != "":
                            self.job_page_url = url
                            break

                if self.job_page_url is None:
                    logger.error(f"❌ Cannot find job listings page for {self.homepage_url}")
                    return False
                else:
                    print(f"Found careers page via fabricated URL: {self.job_page_url}")

            visited_urls.append(self.job_page_url)

            potential_job_listings_site = self.webscraper.get_html_content(self.job_page_url)
            potential_listing_urls = self.urlextractor.get_urls_from_html_file(potential_job_listings_site, self.homepage_url)

            self.job_urls = self.urlextractor.get_urls_from_html_file(potential_listing_urls, blacklist=visited_urls)

            if len(self.job_urls) > 0 and self.job_urls[0].lower() != "none":
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
            job_html = self.webpagescraper.get_html(job_url)
            job_info = self.extract_data_from_job_listing(job_html)
            job_ad = JobAd(
                url=job_url,
                title=job_info['title'],
                description=job_info['description'],
                company=urlparse(self.homepage_url).netloc,
                location=job_info['location'],
                salary=job_info['salary']
            )
            self.write_to_csv(job_ad, output_file)

    def extract_data_from_job_listing(self, html_content: str) -> dict:
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
        logger.info(f"📊 Extracted job information: {job_info}")
        return job_info

    def write_to_csv(self, job_ad: JobAd, filename: str):
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
            logger.info(f"✅ Job ad written to CSV: {job_ad.url}")
        else:
            logger.info(f"⏭️ Job ad already exists in CSV, skipping: {job_ad.url}")


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
