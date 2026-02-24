import os
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from utils.b_scraper.job_scraper.spiders.job_teaser_spider import JobteaserSpider

def run_scraper(date):
    #Tell Scrapy where the settings are relative to your main.py
    os.environ.setdefault('SCRAPY_SETTINGS_MODULE', 'utils.b_scraper.job_scraper.settings')

    # Build the full path: outputs/data 
    folder_path = os.path.join('outputs', f'data[{date}]')
    file_path = os.path.join(folder_path, 'internships.json')

    # Scrapy settings
    settings = get_project_settings()
    settings.set('FEEDS', {
        file_path: {
            'format': 'json',
            'encoding': 'utf8',
            'indent': 4,
            'overwrite': True
        }
    })

    process = CrawlerProcess(settings)
    process.crawl(JobteaserSpider)
    process.start()
   