import pickle
from dotenv import load_dotenv
import os
import spacy
from utils import check_for_techs, dict_to_json, ask_gpt, update_tech_json, get_job_techs, print_attempt_number
import json
import numpy as np
import openai
import boto3
import time

load_dotenv()    

api_key = os.getenv("openai_api_key")
example_text_1 = os.getenv("example_text_1")
example_response_1 = os.getenv("example_response_1")
example_text_2 = os.getenv("example_text_2")
example_response_2 = os.getenv("example_response_2") 

openai.api_key = api_key
nlp = spacy.load("en_core_web_sm")

# AWS no longer going through local files, need to iterate through S3 bucket files
region_name = os.getenv("region_name")
bucket_name = os.getenv("bucket_name")
folder_prefix = "data/"

s3 = boto3.client("s3", region_name=region_name)

clf_object_key = "models/job-desc-classifier-v1.0.pkl"
tfidf_object_key = "models/job-desc-tfidf-vectorizer-v1.0.pkl"

clf_response = s3.get_object(Bucket=bucket_name, Key=clf_object_key)
clf = pickle.load(clf_response["Body"].read())

tfidf_response = s3.get_object(Bucket=bucket_name, Key=tfidf_object_key)
tfidf_vectorizer = pickle.load(tfidf_response["Body"].read())

# List objects in s3 bucket with the given prefix, here to get the data folder
response = s3.list_objects_v2(Bucket=bucket_name, Prefix="data/")
filtered_data_files = [
    obj["Key"] for obj in response.get("Contents", [])
    if obj["Key"].endswith(".json") and obj["Key"].startswith("data/raw")
]

# Go through the filtered files in the data folder
for object_key in filtered_data_files:
    response = s3.get_object(Bucket=bucket_name, key=object_key)
    data = response["Body"].read().decode("utf-8")
    
    print(f"Shortening JDs for {object_key}")
    keylist = list(data.keys())
    # roughly_split to get ~10% of jobs in each split to print progress
    roughly_split = [x[-1] for x in np.array_split(np.array(keylist[:-1]), 10)]
    default_prefix = "p-"

    for key in keylist:
        if key.startswith("metadata"):
            continue
        elif "desc" not in data[key]: #load-in got broken, remove the job
            del data[key]
        else: # it's a job and it has a description which we will try to clean and NER upon
            try:
                cleaned_jd = check_for_techs(data[key]['desc'], tfidf_vectorizer, clf, nlp, 5)
                data[key]["cleaned_desc"] = cleaned_jd
            except Exception as e:
                print(f"Error cleaning JD: {e}")
            try: #JD cleaned, try using model to get techs
                get_job_techs(data, key, keylist, roughly_split)
                time.sleep(2) # add a 2s sleep after each successful API call for now
            except:
                print(f"Error Getting tech list: {e}")
                default_prefix="np-" # change prefix to show this file had at least one error occur
        print(f"")
    # Add metadata            
    data["metadata"]["models"] = {}
    data["metadata"]["models"]["classifier"] = {}
    data["metadata"]["models"]["classifier"]["clf"] = clf_object_key
    data["metadata"]["models"]["classifier"]["tfidf"] = tfidf_object_key
    data["metadata"]["models"]["NER"] = {}
    data["metadata"]["models"]["NER"] = "gpt-3.5-turbo"  # currently only using gpt, after I train my spacy NER model will be using just that so having it be static now is fine.
    
    print(f"Finished processing {object_key}, metadata added")

    # add an 'p-' prefix to show that the object has been processed. 'np-' if an error occured in the techs
    new_object_key = f"data/{default_prefix}-"+object_key[len(folder_prefix):] #without he len(folder_prefix) it'd save as "data/p-data/..." since object_key has the full file structure
    # Put the new data into the bucket, delete the old data.
    s3.put_object(Bucket=bucket_name, Key=new_object_key, Body=data)
    s3.delete_object(Bucket=bucket_name, Key=object_key)
    print(f"Processed file, renamed object: {object_key} -> {new_object_key}")
    
print(f"Finished processing {len(filtered_data_files)} files.")
