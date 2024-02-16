# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
from bs4 import BeautifulSoup as bs
import json
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
import os
from dotenv import load_dotenv

load_dotenv()

class IndscraperPipeline:
    def __init__(self, AWS_ACCESS_KEY_ID=os.getenv("AWS_ACCESS_KEY_ID"), AWS_SECRET_ACCESS_KEY=os.getenv("AWS_SECRET_ACCESS_KEY"), 
                 S3_BUCKET_NAME=os.environ.get("S3_BUCKET_NAME"), S3_PATH_NAME=os.environ.get("S3_PATH_NAME"), SAVE_TO_S3=os.environ.get("SAVE_TO_S3")):
        self.items = []
        self.AWS_ACCESS_KEY_ID = AWS_ACCESS_KEY_ID
        self.AWS_SECRET_ACCESS_KEY = AWS_SECRET_ACCESS_KEY
        self.S3_BUCKET_NAME = S3_BUCKET_NAME
        self.S3_PATH_NAME = S3_PATH_NAME
        self.SAVE_TO_S3 = SAVE_TO_S3
        
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
        test_filename_string = f'{spider.data_filename}.json'
        
        output_file = getattr(spider, 'output_file', test_filename_string)
        with open(output_file, 'w+', encoding='utf-8') as f:
            for item in self.items:
                line = json.dumps(dict(item)) + "\n"
                f.write(line)
                
        if self.SAVE_TO_S3:
            try:
                self.upload_to_s3(spider=spider, filename=test_filename_string)
                spider.log(f"{test_filename_string} saved to S3, deleting local copy")
                os.remove(test_filename_string)
            except Exception as e:
                spider.log(f"Error with upload_to_s3: {e}")
                spider.log(f"Keeping {test_filename_string} stored locally.")
    def upload_to_s3(self, spider, filename):
        s3 = boto3.client('s3', aws_access_key_id=self.AWS_ACCESS_KEY_ID, aws_secret_access_key=self.AWS_SECRET_ACCESS_KEY)
        
        try:
            with open(filename, "rb") as f:
                s3.upload_fileobj(f, self.S3_BUCKET_NAME, fr"data/{filename}")
            spider.log(f"Successfully uploaded {filename} to S3 bucket: {self.S3_BUCKET_NAME}/data")
            
        except NoCredentialsError:
            spider.log("AWS credentials not available. Upload to S3 failed.")
        except ClientError as e:
            if e.response['Error']['Code'] == 'KeyAlreadyExists':
                spider.log(f"Filename (key) {filename} already exists in {self.S3_BUCKET_NAME}/data.")
                new_filename_string = f"new_{filename}"
                try:
                    os.rename(filename, new_filename_string)
                    spider.log(f"Changed {filename} to {new_filename_string}, re-trying save to s3")
                    self.upload_to_s3(spider, filename=new_filename_string)
                except OSError as e:
                    self.log(f"Error renaming file to {new_filename_string}, file stored locally")
            else:
                spider.log(f"Client error uploading to S3: {e}")
        except Exception as e:
            spider.log(f"Error uploading data to S3: {e}")