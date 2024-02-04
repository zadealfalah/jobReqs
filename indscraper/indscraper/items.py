# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class IndscraperItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    pass


class JobItem(scrapy.Item):
    job_key = scrapy.Field()
    keyword = scrapy.Field()
    from_age = scrapy.Field()
    location = scrapy.Field()
    page = scrapy.Field()
    position = scrapy.Field()
    job_title = scrapy.Field()
    company = scrapy.Field()
    job_description = scrapy.Field()
    salary_estimated_flag = scrapy.Field()
    salary_min = scrapy.Field()
    salary_max = scrapy.Field()
    salary_type = scrapy.Field()
    url = scrapy.Field()