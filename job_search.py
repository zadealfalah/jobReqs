from selenium import webdriver
import time
import json
import re
from bs4 import BeautifulSoup as bs
from urllib.parse import urlencode
import threading
import datetime
import os
import boto3 # Add for AWS upload

from utils import get_url, get_job_ids, get_job_data
from globals import k
             
# To be used with a cloudwatch scheduler.  
# Called lambda_function.py in AWS



# def max # threads - remember each needs a driver
max_threads = int(os.environ["max_threads"])
num_pages = int(os.environ["num_pages"])
num_iters = num_pages // max_threads
keyword_list = json.loads(os.environ["keyword_list"])
location_list = json.loads(os.environ["location_list"])
days_ago = os.environ["days_ago"]
region_name = os.environ["region_name"]

job_data =k["job_data"]
job_id_list=k['job_id_list']

start = time.time() # for timing
print(f"Running Indeed Job Search")
print(f"Using {max_threads} drivers and searching {num_pages} pages per keyword/location")
print(f"Looking at posts in the last {days_ago} days.")
print(f"Keywords: {keyword_list}")
print(f"Locations: {location_list}")

threads = []
options = webdriver.FirefoxOptions()
options.add_argument('-headless')  # remove if testing
options.add_argument('-user-data-dir=/tmp')

s3 = boto3.client("s3", region_name=region_name)

def lambda_handler(event, context):
    try:
        driver_list = [webdriver.Firefox(options=options) for x in range(0, max_threads)] # create max_threads num of drivers
        print(f"{len(driver_list)} drivers successfully created")
    except Exception as e:
        print(f"Error creating drivers: {e}")
    end_create_drivers = time.time()
    # job_id_list = init.job_id_list
    # job_data = init.job_data

    for keyword in keyword_list:
        for location in location_list:
            # print(f"Searching for {keyword} in {location}")
            for i in range(0, num_iters):
                for j in range(0, max_threads):
                    old_jobs_flag = False  # flag to break multiple loops if jobs repeat
                    offset = i*10*max_threads + j*10
                    print(f"Searching for {keyword} in {location} on page {int((offset/10)+1)}")
                    # print(offset)
                    t = threading.Thread(args=(driver_list[j], keyword, location, offset, days_ago), target=get_job_ids) 
                    t.start()
                    threads.append(t)
                    
                    for t in threads:
                        t.join()
    # print(f"Threads results:")
    # print([thread.result() for thread in threads]) #doesn't work, how to set the old_jobs_flag with a thread??
    end_find_jobs = time.time()

    print(f"Found {len(job_id_list)} job combos.")
    print(f"Getting Job Details")                
    for i in range(0, len(job_id_list), max_threads):
        jobs_subset = job_id_list[i:i+10]
        threads = []
        for j in range(0, len(jobs_subset)):
            # print(jobs_subset)
            t = threading.Thread(args=(driver_list[j], jobs_subset[j]), target=get_job_data)
            t.start()
            threads.append(t)
            
            for t in threads:
                t.join()

    print(f"Searched for {len(job_data.keys())} job descriptions.")
    end_get_descs = time.time()


    date_info = datetime.datetime.now()
    date_str = date_info.strftime('%d-%m-%y')
    full_time_str = date_info.strftime('%H:%M:%S-%d-%m-%y')

    ### Could add metadata inf on to json before saving it e.g. the time to run each part, time to complete, keywords used, etc.
    ### Would certainly save space in the json file names doing it like that too!

    job_data["metadata"] = {}
    job_data["metadata"]["keywords"] = keyword_list
    job_data["metadata"]["locations"] = location_list
    job_data["metadata"]["time_ran"] = full_time_str
    job_data["metadata"]["num_jobs"] = len(job_data.keys())

    job_data["metadata"]["timings"] = {}
    job_data["metadata"]["timings"]["start_drivers"] = (end_create_drivers - start)
    job_data["metadata"]["timings"]["find_job_ids"] = (end_find_jobs - end_create_drivers)
    job_data["metadata"]["timings"]["get_job_descs"] = (end_get_descs - end_find_jobs)


    json_file_name = fr"raw_data-{date_str}.json"

    # dict_to_json(job_data, json_file_name)
    # print(f"New search saved to: {json_file_name}")
    # When running locally, I used dict_to_json(job_data, json_file_name)
    # Now that we are using MWAA and Lambda on AWS, we must change it.
    json_job_data = json.dumps(job_data)

    # new env vars for aws
    region_name = os.environ["region_name"]
    bucket_name = os.environ["bucket_name"]
    object_key = fr"data/{json_file_name}"


    s3.put_object(Bucket=bucket_name, Key=object_key, Body=json_job_data)
    print(f"JSON data saved to S3 bucket '{bucket_name}' with object key '{object_key}'")


    ## ChatGPT at least says that shutting down drivers isn't necessary with Lambda.  
    # start_shutdown_driver = time.time()
    # try:
    #     for driver in driver_list:
    #         driver.quit()
    #     print(f"Drivers have been closed")
    # except:
    #     print("Error closing drivers!")
    # end_shutdown_driver = time.time()
        
    print(f"Starting the drivers took {round(end_create_drivers - start,2)}s, "
        f"Finding the jobs took {round((end_find_jobs - end_create_drivers)/60,2)}m, "
        f"Getting the job descriptions took {round((end_get_descs - end_find_jobs)/60,2)}m, "
        f"So in total this took {round((end_get_descs - start)/60,2)}m if we don't have to shut down the drivers.\n")
    #   f"If we do have to shut down the drivers, it adds on another {round(end_shutdown_driver - start_shutdown_driver,2)}s")