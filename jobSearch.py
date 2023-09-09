from selenium import webdriver
import time
import json
import re
from bs4 import BeautifulSoup as bs
from urllib.parse import urlencode
import threading
import datetime
import os
from dotenv import load_dotenv



def get_url(query:str, location:str, offset=0, days_ago=1):
    params = {"q":query, "l":location, "filter":0, "start":offset, "fromage":days_ago}
    return "https://www.indeed.com/jobs?" + urlencode(params)


## Seems to throw lots of errors with 'Error list index out of range'
## Presumably from looking for job searches with few pages but for some reason continuing to .get()
## e.g. on 09/07/23 looking with (driver, 'mle', 'remote', offset, '1')
## Had LOTS of list index out of range errors.
def get_job_ids(driver, keyword, location, offset, days_ago):
    global job_id_list
    
    indeed_jobs_url = get_url(keyword, location, offset, days_ago)
    try:
        driver.get(indeed_jobs_url)
        # time.sleep(np.random.uniform(1, 2))
        response = driver.page_source  # get the html of the page
        script_tag = re.findall(r'window.mosaic.providerData\["mosaic-provider-jobcards"\]=(\{.+?\});', response)
        if script_tag is not None:
            json_blob = json.loads(script_tag[0])
            jobs_list = json_blob['metaData']['mosaicProviderJobCardsModel']['results']
            for i, job in enumerate(jobs_list):
                if (job.get('jobkey') is not None) & (job.get('jobkey') not in job_id_list):
                    job_id_list.append((job.get('jobkey'), keyword))
            # if len(jobs_list) < 10:
            #     break
    except Exception as e:
        print("Error", e)



def get_job_data(driver, job_id):
    global job_data
    
    # If the job id is already in job_data
    if job_id[0] in job_data:
        # For some reason I am getting job_data[jobid[0]]['terms'] with duplicated terms e.g. ['data analyst', 'machine learning', 'machine learning']
        # No idea why.  Threading issue?  To avoid this for now will explicitly only allow non-duplicated terms
        # I think it may be because of things like pg 43 being last page of a search but pg 44+ returning the same results. below if-pass should fix it for now.
        if job_id[1] in job_data[job_id[0]]['terms']:
            pass
        else:
            job_data[job_id[0]]['terms'].append(job_id[1]) # add the search term used to the terms 
        
    else:  # new job ID
        job_data[job_id[0]] = {}  # create empty nested dict with job id as key
        job_data[job_id[0]]['terms'] = [] # create empty list to be appended to with search terms
        try:
            indeed_job_url = "https://www.indeed.com/m/basecamp/viewjob?viewtype=embdedded&jk=" + job_id[0]
            # print(indeed_job_url)
            driver.get(indeed_job_url)
            # time.sleep(np.random.uniform(1, 2))
            response = driver.page_source
            script_tag  = re.findall(r"_initialData=(\{.+?\});", response)
            if script_tag is not None:
                json_blob = json.loads(script_tag[0])
                job = json_blob["jobInfoWrapperModel"]["jobInfoModel"]
                
                #Getting salary info
                # If the salary info is provided by the company itself
                if json_blob["salaryInfoModel"] is not None: 
                    job_data[job_id[0]]["salary_min"] = json_blob["salaryInfoModel"]["salaryMin"]
                    job_data[job_id[0]]["salary_max"] = json_blob["salaryInfoModel"]["salaryMax"]
                # If instead the salary is an estimate from indeed
                elif json_blob["salaryGuideModel"]["estimatedSalaryModel"] is not None:
                    job_data[job_id[0]]["salary_min"] = json_blob["salaryGuideModel"]["estimatedSalaryModel"]["min"]
                    job_data[job_id[0]]["salary_max"] = json_blob["salaryGuideModel"]["estimatedSalaryModel"]["max"]
                # If salary has none from company nor an estimate from indeed    
                else:
                    job_data[job_id[0]]["salary_min"] = None
                    job_data[job_id[0]]["salary_max"] = None    
                
                job_data[job_id[0]]['terms'].append(job_id[1]) # start the list of search terms with the term used here
                job_data[job_id[0]]['title'] = job.get('jobInfoHeaderModel').get('jobTitle') if job.get('jobInfoHeaderModel') is not None else ''
                job_data[job_id[0]]["company"] = job.get('jobInfoHeaderModel').get('companyName') if job.get('jobInfoHeaderModel') is not None else ''
                temp_desc = job.get('sanitizedJobDescription').strip() if job.get('sanitizedJobDescription') is not None else '' # html string
                no_html_desc = bs(temp_desc, 'html.parser').get_text(separator=' ').strip()
                job_data[job_id[0]]['desc'] = no_html_desc
                # job_data[job_id[0]]['test'] = job.get('jobDescriptionText').get('jobDescriptionText') if job.get('jobDescriptionText') is not None else ''
                

        except Exception as e:
            print("Error", e)
            
            
def dict_to_json(dict, filepath):
    with open(filepath, "w") as out:
        json.dump(dict, out)
        

load_dotenv()        

# def max # threads - remember each needs a driver
max_threads = int(os.getenv("max_threads"))
num_pages = int(os.getenv("num_pages"))
num_iters = num_pages // max_threads
keyword_list = json.loads(os.getenv("keyword_list"))
location_list = json.loads(os.getenv("location_list"))
days_ago = os.getenv("days_ago")

start = time.time() # for timing
print(f"Running Indeed Job Search")
print(f"Using {max_threads} drivers and searching {num_pages} pages per keyword/location")
print(f"Looking at posts in the last {days_ago} days.")
print(f"Keywords: {keyword_list}")
print(f"Locations: {location_list}")

threads = []
options = webdriver.FirefoxOptions()
options.add_argument('-headless')  # remove if testing
try:
    driver_list = [webdriver.Firefox(options=options) for x in range(0, max_threads)] # create max_threads num of drivers
    print(f"{len(driver_list)} drivers successfully created")
except:
    print(f"Error creating drivers")
end_create_drivers = time.time()
job_id_list = []
job_data = {}
for keyword in keyword_list:
    for location in location_list:
        # print(f"Searching for {keyword} in {location}")
        for i in range(0, num_iters):
            for j in range(0, max_threads):
                offset = i*10*max_threads + j*10
                print(f"Searching for {keyword} in {location} on page {int((offset/10)+1)}")
                # print(offset)
                t = threading.Thread(args=(driver_list[j], keyword, location, offset, days_ago), target=get_job_ids) 
                t.start()
                threads.append(t)
                
                for t in threads:
                    t.join()
end_find_jobs = time.time()
print(f"Found {len(job_id_list)} jobs.")
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
job_data["metadata"]["num_jobs"] = len(job_id_list)

job_data["metadata"]["timings"] = {}
job_data["metadata"]["timings"]["start_drivers"] = (end_create_drivers - start)
job_data["metadata"]["timings"]["find_job_ids"] = (end_find_jobs - end_create_drivers)
job_data["metadata"]["timings"]["get_job_descs"] = (end_get_descs - end_find_jobs)


json_file_name = fr"data/raw_data-{date_str}.json"

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
    
print(f"Starting the drivers took {end_create_drivers - start}s, "
      f"Finding the jobs took {(end_find_jobs - end_create_drivers)/60}m, "
      f"Getting the job descriptions took {(end_get_descs - end_find_jobs)/60}m, "
      f"So in total this took {end_get_descs - start}m if we don't have to shut down the drivers.\n"
      f"If we do have to shut down the drivers, it adds on another {end_shutdown_driver - start_shutdown_driver}s")