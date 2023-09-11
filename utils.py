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

from globals import k


def get_url(query:str, location:str, offset=0, days_ago=1):
    params = {"q":query, "l":location, "filter":0, "start":offset, "fromage":days_ago}
    return "https://www.indeed.com/jobs?" + urlencode(params)

def dict_to_json(dict, filepath):
    with open(filepath, "w") as out:
        json.dump(dict, out)


def get_job_ids(driver, keyword, location, offset, days_ago):
    job_id_list=k['job_id_list']
    
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
    job_data =k["job_data"]
    
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