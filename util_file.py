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
# import openai
# import numpy as np


from global_file import k


def get_url(query:str, location:str, offset=0, days_ago=1):
    params = {"q":query, "l":location, "filter":0, "start":offset, "fromage":days_ago}
    return "https://www.indeed.com/jobs?" + urlencode(params)

def dict_to_json(dict, filepath):
    with open(filepath, "w") as out:
        json.dump(dict, out)
        
        
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
            
            

                
                
def remove_processing(filepath, delete_processed = True):
    """Used to remove processing leaving only the raw data for reuse.

    Args:
        filepath (_type_): _description_
    """
    with open(filepath) as f:
        data = json.load(f)
    for key in data.keys():
        try:
            del data[key]["cleaned_desc"]
        except:
            print(f"{key} has no cleaned desc")
            continue
        try:
            del data[key]["techs"]
        except:
            print(f"{key} has no techs")
            continue
        if key == "metadata":
            try:
                del data[key]["models"]
            except:
                print(f"{key} has no metadata models")
                continue
    unprocessed_str = filepath.replace("p-", "")
    dict_to_json(data, unprocessed_str)
    if delete_processed == True:
        os.remove(filepath)
        print(f"File {filepath} has been removed, and file {unprocessed_str} has been recreated.")
    else:
        print(f"File {unprocessed_str} has been recreated.  The original file {filepath} was not deleted.")
        
        
        
def get_filelist(start_date, end_date, folder_path='data', start_str='p-raw'):
    """Get the json files which start with {start_str} in the {folder_path} within the date range (inclusive).

    Args:
        start_date (str): String start date in dd-mm-yy format - e.g. 11-09-23
        end_date (str): String end date in dd-mm-yy format - e.g. 17-10-23
        folder_path (str, optional): Folder path to search within. Defaults to 'data'.
        start_str (Str, optional): Starting string for files to pull. Defaults to 'p-raw'
    Returns:
        files_between_dates (list): List of strings, where each string is a filename from {folder_path} beginning with {start_str}
        and within [{start_date}, {end_date}]
    """
    start_date = datetime.datetime.strptime(start_date, "%d-%m-%y")
    end_date = datetime.datetime.strptime(end_date, "%d-%m-%y")
    
    files_between_dates = []
    
    for filename in os.listdir(folder_path):
        if filename.startswith(start_str):
            try:
                # Extract the date from the file name
                file_date = datetime.datetime.strptime(filename[11:19], "%d-%m-%y")
                if start_date <= file_date <= end_date:
                    files_between_dates.append(filename)
            except ValueError:
                # In case the date in the file name is not in the expected format
                pass
    
    return files_between_dates