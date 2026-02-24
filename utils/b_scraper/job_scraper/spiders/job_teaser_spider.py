import scrapy
import os
from scrapy_playwright.page import PageMethod

class JobteaserSpider(scrapy.Spider):
    name = "jobteaser"

    async def start(self):
        # Locate the links.txt file
        links_file = os.path.join('utils/b_scraper', 'links.txt')

        if not os.path.exists(links_file):
            self.logger.error(f"links.txt NOT FOUND at {links_file}")
            return

        # 2. Read the file and yield a request for each URL
        with open(links_file, 'r') as f:
            urls = [line.strip() for line in f if line.strip()]

        for url in urls:
            self.logger.info(f"Starting scrape for: {url}")
            yield scrapy.Request(
                url,
                meta={
                    "playwright": True,
                    "playwright_page_methods": [
                        PageMethod("wait_for_selector", "a.JobAdCard_link__LMtBN"),
                    ],
                },
                callback=self.parse
            )

    def parse(self, response):
        offers = response.css('a.JobAdCard_link__LMtBN')
        for offer in offers:
            yield response.follow(
                offer, 
                callback=self.parse_details,
                meta={
                    "playwright": True,
                    "playwright_page_methods": [
                        PageMethod("wait_for_selector", 'article[data-testid="jobad-DetailView__Description"]'),
                    ],
                }
            )

    def parse_details(self, response):
        # Data extraction using the stable data-testid selectors from your HTML file
        description_parts = response.css('article[data-testid="jobad-DetailView__Description"] ::text').getall()
        clean_content = " ".join([text.strip() for text in description_parts if text.strip()])

        yield {
            'URL': response.url,
            'name': response.css('h1[data-testid="jobad-DetailView__Heading__title"]::text').get(default='').strip(),
            'company': response.css('h2[data-testid="jobad-DetailView__Heading__company_name"]::text').get(default='').strip(),
            'location': response.css('p[data-testid="jobad-DetailView__CandidacyDetails__Locations"]::text').get(default='').strip(),
            'content': clean_content
        }