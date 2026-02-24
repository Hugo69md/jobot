# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class JobScraperItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    URL = scrapy.Field()
    name = scrapy.Field()
    company = scrapy.Field()
    location = scrapy.Field()
    content = scrapy.Field()
