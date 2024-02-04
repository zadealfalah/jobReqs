# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
from bs4 import BeautifulSoup as bs
import json

class IndscraperPipeline:
    def __init__(self):
        self.items = []
        
    def process_item(self, item, spider):
        
        adapter = ItemAdapter(item)
        
        
        ## jobTitle, company --> Strip white space, lowercase
        to_strip_keys = ['job_title', 'company']
        for to_strip_key in to_strip_keys:
            value = adapter.get(to_strip_key)
            adapter[to_strip_key] = value.lower().strip()
        
        
        ## jobDescription --> Parse html, remove whitespace
        jd_string = adapter.get('job_description')
        no_html_string = bs(jd_string, 'html.parser').get_text(separator=' ').strip()
        # no_html_string = no_html_string.replace('\n', ' ') # Keep newlines for now for binary classifier?
        adapter['job_description'] = no_html_string
        
        ## salary_min, salary_max, salary_type --> Yearly
        salary_value_keys = ['salary_min', 'salary_max']
        salary_type_start = adapter.get('salary_type')
        if salary_type_start == 'YEARLY':  # Salary already yearly
            pass
        elif salary_type_start is not None: # Salary is hourly instead, convert assuming 2080 hrs/yr (40hrs/wk)
            for salary_value_key in salary_value_keys:
                value = adapter.get(salary_value_key)
                adapter[salary_value_key] = value * 2080
                adapter['salary_type'] = 'YEARLY'
        else: # It's a None object
            pass
        
        self.items.append(item)
        return item

    def close_spider(self, spider):
        # After the spider has finished scraping, update the 'keyword' field for each item
        for item in self.items:
            job_key = item['job_key']
            if job_key in spider.job_links:
                item['keyword'] = spider.job_links[job_key]
        
        # Write the updated items to the JSON file
        output_file = getattr(spider, 'output_file', f'data/{spider.data_filename}_processed.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            for item in self.items:
                line = json.dumps(dict(item)) + "\n"
                f.write(line)