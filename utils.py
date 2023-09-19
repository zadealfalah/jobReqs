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
import openai
import numpy as np
from tenacity import retry, stop_after_attempt, wait_random_exponential


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
            new_jobs_list = [] #Store the new jobs for this run alone, used to find when pages are repeating
            for i, job in enumerate(jobs_list):
                new_jobs_list.append(job)
                if (job.get('jobkey') is not None) & (job.get('jobkey') not in job_id_list):
                    job_id_list.append((job.get('jobkey'), keyword))
        
        return new_jobs_list
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
            
            
def check_for_techs(text, vectorizer, clf, nlp, n=5):
    original_text = text
    
    # Don't use split function as we don't want the output I use to label them manually.
    splits = text.count("\n")//n
    split_text = re.findall("\n".join(["[^\n]+"]*splits), original_text)
    processed = [" ".join([token.lemma_ for token in nlp(para)]) for para in split_text]
    
    transformed = vectorizer.transform(processed)
    pred_vals = clf.predict(transformed)
    
    zipped_paras = list(zip(split_text, pred_vals))
    # return(zipped_paras)
    cleaned = " ".join([text for (text, label) in zipped_paras if label == 1])
    return cleaned.strip("\n")  # add on stripping the newlines from the cleaned descs to lower # tokens



def ask_gpt(text, example_text_1=os.getenv("example_text_1"), example_text_2=os.getenv("example_text_2"), example_response_1=os.getenv("example_response_1"), example_response_2=os.getenv("example_response_2")):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role":"system", "content":"You list specific technologies from texts separated by commas."},
            {"role":"user", "content":f"Report ONLY specific tools and technologies from the following text as a comma separated list.  Do not return generics like 'data processing': {example_text_1}"},
            {"role":"assistant", "content":f"{example_response_1}"},
            {"role":"user", "content":f"Report ONLY specific tools and technologies from the following text as a comma separated list.  Do not return generics like 'data processing': {example_text_2}"},
            {"role":"assistant", "content":f"{example_response_2}"},
            {"role":"user", "content":f"Report ONLY specific tools and technologies from the following text as a comma separated list.  Do not return generics like 'data processing': {text}"}
        ]
    )
    return response


def print_attempt_number(retry_state):
    print(f"Retrying: {retry_state.attempt_number}...")
@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6), after=print_attempt_number)
def get_job_techs(data, key, keylist, roughly_split):
    if key.startswith("metadata"):
        return #metadata key, ignore it
    if key in roughly_split:
        print(f"~{(roughly_split.index(key)+1)*10}% done")
    if "cleaned_desc" not in data[key]: #no cleaned desc as loading in desc failed
        del data[key]
    if len(data[key]["cleaned_desc"]) > 1: #there are jds that seemed to contain no techs after classifier, ignore those
        data[key]["techs"] = [x.lower() for x in ask_gpt(data[key]["cleaned_desc"])["choices"][0]["message"]["content"].split(", ")]
        # print(data[key]["techs"])
    else:
        data[key]["techs"] = ""
        
        
def update_tech_json(datapath="data", prefix='p-', startstr="raw_data"):
    for filename in os.listdir(datapath):
        if filename.startswith(startstr): # just with one file at first
            print(f"Processing {filename}")
            filepath = fr"data/{filename}"
            with open(filepath) as f:
                data = json.load(f)
            keylist = list(data.keys())
            print(f"There are {len(keylist)-1} jobs in {filename}")
            roughly_split = [x[-1] for x in np.array_split(np.array(keylist[:-1]), 10)]
            for key in keylist:
                # print(f"Before: {key}, \n {data[key]['techs']}")
                #Formatted like this so that the retrys are by-key rather than by-file
                try:
                    get_job_techs(data, key, keylist, roughly_split)
                except Exception as e:
                    print(f"Error getting tech list: {e}")
                    prefix = 'np-' # change prefix to show this file had at least one error occur
                time.sleep(2) # add sleep see if it fixes the timeouts.
                # print(f"After: {data[key]['techs']}")
                
            # data['metadata']['gpt'] = {}   #should add the gpt metadata to this after making it all into env vars for ask_gpt()
            # data['metadata']['gpt']['prompt']
            
            dict_to_json(data, fr"{datapath}/{filename}") #after going through all keys, update the json file
            
            try:
                os.rename(fr"{datapath}/{filename}", fr"{datapath}/{prefix}{filename}") #update the filename with p- to show it's been processed
                print(f"{filepath} renamed to {datapath}/{prefix}{filename}")
            except FileExistsError as e:
                print(f"File {datapath}/{prefix}{filename} already exists")
                print(f"Saving as {datapath}/{prefix}{filename}-1")
                os.rename(fr"{datapath}/{filename}", fr"{datapath}/{prefix}{filename}-1")
                print(f"{filepath} renamed to {datapath}/{prefix}{filename}-1")
                
                

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