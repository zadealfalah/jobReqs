import re
import json
import scrapy
from urllib.parse import urlencode
from bs4 import BeautifulSoup as bs
from indscraper.items import JobItem
from datetime import datetime

class IndeedjobsSpider(scrapy.Spider):
    name = "indeedjobs"
    allowed_domains = ["www.indeed.com", "proxy.scrapeops.io"]
    start_urls = ["https://www.indeed.com"]
    
    todays_date = datetime.today().strftime('%d_%m_%Y')
    
    job_links = {}

    data_filename = f"test_replace_{todays_date}.json"
    ## Overwrite settings.py, set format to json and to overwrite the file when we run the spider
    custom_settings = {
        'FEEDS' : {
            f'data/{data_filename}' : {'format':'json', 'overwrite':True},
        },
        'output_file': f'data/{data_filename}_processed.json',
    }
    
    def get_indeed_search_url(self, keyword, location, offset=0, fromage=1): #age in terms of # days
        parameters = {"q": keyword, "l": location, "filter": 0, "start": offset, "fromage":fromage}
        return "https://www.indeed.com/jobs?" + urlencode(parameters)


    def start_requests(self):
        keyword_list = ['data science', 'data analyst', 'data engineer', 'machine learning engineer']
        # keyword_list = ['data science', 'data scientist']
        location_list = ['remote']
        for keyword in keyword_list:
            for location in location_list:
                # self.logger.info(f"Searching for {keyword} in {location}")
                indeed_jobs_url = self.get_indeed_search_url(keyword, location)
                yield scrapy.Request(url=indeed_jobs_url, callback=self.parse_search_results, meta={'keyword': keyword, 'location': location, 'offset': 0, 'fromage': 1})

    def parse_search_results(self, response):
        location = response.meta['location']
        keyword = response.meta['keyword'] 
        offset = response.meta['offset'] 
        fromage = response.meta['fromage']
        # visited_urls = response.meta.get('visited_urls', set())
        
        script_tag  = re.findall(r'window.mosaic.providerData\["mosaic-provider-jobcards"\]=(\{.+?\});', response.text)
        if script_tag is not None:
            json_blob = json.loads(script_tag[0])

            # Paginate Through Jobs Pages
            if offset == 0:
                meta_data = json_blob["metaData"]["mosaicProviderJobCardsModel"]["tierSummaries"]
                num_results = sum(category["jobCount"] for category in meta_data)
                if num_results > 1000: # To generate the offsets
                    num_results = 50
                
                job_urls = set()
                for offset in range(0, num_results + 10, 10):
                # for offset in range(0, 10, 10):  # testing amount, only first page
                    url = self.get_indeed_search_url(keyword, location, offset, fromage)
                    yield scrapy.Request(url=url, callback=self.parse_search_results, meta={'keyword': keyword, 'location': location, 'offset': offset, 'fromage': fromage, 'job_urls': job_urls})

            ## Extract Jobs From Search Page
            jobs_list = json_blob['metaData']['mosaicProviderJobCardsModel']['results']
            for index, job in enumerate(jobs_list):
                if job.get('jobkey') is not None:
                    job_url = 'https://www.indeed.com/m/basecamp/viewjob?viewtype=embedded&jk=' + job.get('jobkey')
                    try:
                        self.log(f"Job key {job.get('jobkey')} already seen. Adding keyword {keyword} to job_links")
                        self.job_links[job.get('jobkey')] += [keyword]
                    except KeyError:
                        self.log(f"Job key {job.get('jobkey')} not yet seen. Adding keyword {keyword} to job_links")
                        self.job_links[job.get('jobkey')] = [keyword]
                    job_urls.add(job_url)
                    yield scrapy.Request(url=job_url, 
                            callback=self.parse_job, 
                            meta={
                                'keyword': keyword, 
                                'location': location, 
                                'fromage': fromage,
                                'page': round(offset / 10) + 1 if offset > 0 else 1,
                                'position': index,
                                'jobKey': job.get('jobkey'),
                                'url': job_url,
                            })

    def parse_job(self, response):
        job_item = JobItem()
    
        job_item['job_key'] = response.meta['jobKey']
        job_item['location'] = response.meta['location']
        job_item['keyword'] = [response.meta['keyword']]
        job_item['from_age'] = response.meta['fromage']
        job_item['page'] = response.meta['page'] 
        job_item['position'] = response.meta['position'] 
        script_tag  = re.findall(r"_initialData=(\{.+?\});", response.text)
        if script_tag is not None:
            json_blob = json.loads(script_tag[0])
            job = json_blob["jobInfoWrapperModel"]["jobInfoModel"]

            ## Getting salary info
            if json_blob["salaryInfoModel"] is not None: # Salary info from company itself
                job_item['salary_min'] = json_blob['salaryInfoModel']['salaryMin']
                job_item['salary_max'] = json_blob['salaryInfoModel']['salaryMax']
                job_item['salary_type'] = json_blob['salaryInfoModel']['salaryType']
                job_item['salary_estimated_flag'] = 0
            elif json_blob["salaryGuideModel"]["estimatedSalaryModel"] is not None: # Salary estimate from Indeed
                job_item['salary_min'] = json_blob["salaryGuideModel"]["estimatedSalaryModel"]["min"]
                job_item['salary_max'] = json_blob["salaryGuideModel"]["estimatedSalaryModel"]["max"]
                job_item['salary_type'] = json_blob['salaryGuideModel']['estimatedSalaryModel']["type"]
                job_item['salary_estimated_flag'] = 1
            else: # Salary not visible from either company or Indeed
                job_item['salary_min'] = None
                job_item['salary_max'] = None
                job_item['salary_type'] = None
                job_item['salary_estimated_flag'] = 0
            

            job_item['job_description'] = job.get('sanitizedJobDescription') if job.get('sanitizedJobDescription') is not None else '' # html string
            job_item['company'] = job.get('jobInfoHeaderModel').get('companyName') if job.get('jobInfoHeaderModel') is not None else ''
            job_item['job_title'] = job.get('jobInfoHeaderModel').get('jobTitle') if job.get('jobInfoHeaderModel') is not None else ''
            
            job_item['url'] = response.meta['url']
            
            # Append the job_item to the 'items' key in the meta attribute
            response.meta.setdefault('items', []).append(job_item)
            
            yield job_item

    # def closed(self, reason):
    #     self.log(f"Final job links:")
    #     self.log(f"{self.job_links}")
    #     self.log(f"End items:")
    #     processed_items = getattr(self, 'items', [])
    #     for item in processed_items:
    #         # self.log(f"Item: {item}")
    #         item['keyword'] = self.job_links[item['job_key']]
    #         yield item