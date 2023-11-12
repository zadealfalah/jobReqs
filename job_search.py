from selenium import webdriver
from selenium.webdriver.firefox.options import Options 
# Switch to chromedriver for AWS
# from selenium.webdriver.chrome.options import Options
# from selenium_stealth import stealth
import time
import json
import re
from bs4 import BeautifulSoup as bs
from urllib.parse import urlencode
import threading
import datetime
import os
from dotenv import load_dotenv
import sys
import numpy as np

from utils import get_url, dict_to_json, get_job_data
from globals import k
        
from collections import deque, defaultdict

load_dotenv()        

### add check to see if file already exists for that day.
date_info = datetime.datetime.now()
date_str = date_info.strftime('%d-%m-%y')
full_time_str = date_info.strftime('%H:%M:%S-%d-%m-%y')
json_file_name = fr"data/raw_data-{date_str}.json"
if os.path.isfile(json_file_name):
    print(f"{json_file_name} already exists!")
    print(f"Exiting job_search.py")
    sys.exit()


# def max # threads - remember each needs a driver
max_threads = int(os.getenv("max_threads"))
num_pages = int(os.getenv("num_pages"))
num_iters = num_pages // max_threads
keyword_list = json.loads(os.getenv("keyword_list"))
# keyword_list = ['mle'] # for testing
location_list = json.loads(os.getenv("location_list"))
days_ago = os.getenv("days_ago")

# init() #init the global job_data and job_id_list variables
job_data =k["job_data"]
job_id_list=k['job_id_list']

start = time.time() # for timing
print(f"Running Indeed Job Search")
print(f"Job data will be saved to {json_file_name}")
print(f"Using {max_threads} drivers and searching {num_pages} pages per keyword/location")
print(f"Looking at posts in the last {days_ago} days.")
print(f"Keywords: {keyword_list}")
print(f"Locations: {location_list}")


def create_threaded_drivers(num_drivers=max_threads):
    threads = []
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--single-process')
    options.add_argument('--disable-dev-shm-usage')
    try:
        driver_list = [webdriver.Firefox(options=options) for x in range(0, num_drivers)] # create max_threads num of drivers
        print(f"{len(driver_list)} drivers successfully created")
    except Exception as e:
        print(f"Error creating drivers: {e}")
    return threads, driver_list


threads, driver_list = create_threaded_drivers()
end_create_drivers = time.time()


# print(f"Searching for {keyword} in {location} on page {int((offset/10) + 1)}")

# Create an event object to signal the threads to stop
stop_event = threading.Event()

# Create a dictionary to track job keys for each keyword and location
job_keys_dict = defaultdict(set)

# Create a deque to keep track of the last 10 job keys
last_10_job_keys = deque(maxlen=10)

def get_job_ids(driver, keyword, location, offset, days_ago):
    job_id_list = k['job_id_list']
    indeed_jobs_url = get_url(keyword, location, offset, days_ago)
    try:
        driver.get(indeed_jobs_url)
        response = driver.page_source
        script_tag = re.findall(r'window.mosaic.providerData\["mosaic-provider-jobcards"\]=(\{.+?\});', response)
        if script_tag is not None:
            json_blob = json.loads(script_tag[0])
            jobs_list = json_blob['metaData']['mosaicProviderJobCardsModel']['results']

            for i, job in enumerate(jobs_list):
                if stop_event.is_set():
                    return  # Exit the function if the event is set

                if job.get('jobkey') is not None:
                    job_key = job.get('jobkey')
                    
                    job_keys_in_current_iteration = set([job_key] + list(last_10_job_keys))
                    
                    if set(last_10_job_keys) == job_keys_in_current_iteration:
                        # Detected repeating job keys in the last 10 jobs, set the stop event
                        stop_event.set()
                        return  # Exit the function

                    last_10_job_keys.append(job_key)
                    job_keys_dict[(keyword, location)].add(job_key)
                    job_id_list.append((job_key, keyword))

    except Exception as e:
        if "list index out of range" in str(e):
            # Handling the specific exception "list index out of range"
            print(f"List index out of range - term {keyword} probably not found.")
            stop_event.set()
            return  # Exit the function

# Iterate through your loops
for keyword in keyword_list:
    for location in location_list:
        stop_event.clear()  # Clear the stop event for each new location
        job_keys_dict[(keyword, location)] = set()  # Clear the job keys set for each new location
        last_10_job_keys.clear()  # Clear the last 10 job keys for each new location
        
        found_repeating_job_keys = False  # Flag to track if repeating job keys were found
        
        for i in range(0, num_iters):
            threads = []

            for j in range(0, max_threads):
                offset = i * 10 * max_threads + j * 10
                print(f"Searching for {keyword} in {location} on page {int((offset/10) + 1)}")
                t = threading.Thread(args=(driver_list[j], keyword, location, offset, days_ago), target=get_job_ids)
                t.start()
                threads.append(t)

            # Join the threads to wait for them to finish
            for t in threads:
                t.join()

            if stop_event.is_set():
                found_repeating_job_keys = True  # Set the flag if repeating job keys were found
                break  # Exit the inner loop

        if found_repeating_job_keys:
            print(f"Found repeating job keys, move to next.")
            # Exit the outer loop to move to the next location
            break




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


### Could add metadata inf on to json before saving it e.g. the time to run each part, time to complete, keywords used, etc.
### Would certainly save space in the json file names doing it like that too!

job_data["metadata"] = {}
job_data["metadata"]["keywords"] = keyword_list
job_data["metadata"]["locations"] = location_list
job_data["metadata"]["time_ran"] = full_time_str
job_data["metadata"]["num_jobs"] = len(job_data.keys()) - 1

job_data["metadata"]["timings"] = {}
job_data["metadata"]["timings"]["start_drivers"] = (end_create_drivers - start)
job_data["metadata"]["timings"]["find_job_ids"] = (end_find_jobs - end_create_drivers)
job_data["metadata"]["timings"]["get_job_descs"] = (end_get_descs - end_find_jobs)



dict_to_json(job_data, json_file_name)
print(f"New search saved to: {json_file_name}")
## Don't think I need to close this as I can instead shut down
## The AWS instance.  Shutting them down takes ~30s so it would save a lot of time
start_shutdown_driver = time.time()
try:
    for driver in driver_list:
        driver.quit()
    print(f"Drivers have been closed")
except:
    print("Error closing drivers!")
end_shutdown_driver = time.time()
    
print(f"Starting the drivers took {round(end_create_drivers - start,2)}s, "
      f"Finding the jobs took {round((end_find_jobs - end_create_drivers)/60,2)}m, "
      f"Getting the job descriptions took {round((end_get_descs - end_find_jobs)/60,2)}m, "
      f"So in total this took {round((end_get_descs - start)/60,2)}m if we don't have to shut down the drivers.\n"
      f"If we do have to shut down the drivers, it adds on another {round(end_shutdown_driver - start_shutdown_driver,2)}s")