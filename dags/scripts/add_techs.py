import pickle
from dotenv import load_dotenv
import os
import spacy
from utils.util_file import dict_to_json
import json
import numpy as np
import openai
from tenacity import retry, stop_after_attempt, wait_random_exponential
import time
import re



load_dotenv()    

api_key = os.getenv("openai_api_key")
gpt_model = os.getenv("gpt_model")
gpt_prompt = os.getenv("gpt_prompt")
example_prompt = os.getenv("example_prompt")
example_text_1 = os.getenv("example_text_1")
example_response_1 = os.getenv("example_response_1")
example_text_2 = os.getenv("example_text_2")
example_response_2 = os.getenv("example_response_2") 

saved_clf = os.getenv("saved_clf")
saved_tfidf = os.getenv("saved_tfidf")



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



def ask_gpt(text, gpt_model=gpt_model, gpt_prompt=gpt_prompt, example_prompt=example_prompt, example_text_1=example_text_1, example_text_2=example_text_2, example_response_1=example_response_1, example_response_2=example_response_2):
    # print(f"gpt_model: {gpt_model}")
    # print(f"gpt_prompt: {gpt_prompt}")
    # print(f"example text 1: {example_text_1}")
    # print(f"example response 1: {example_response_1}")
    # print(f"example text 2: {example_text_2}")
    # print(f"example response 2: {example_response_2}")
    # print(f"text: {text}")
    response = openai.ChatCompletion.create(
        model=gpt_model,
        messages=[
            {"role":"system", "content":f"{gpt_prompt}"},
            {"role":"user", "content":f"{example_text_1}"},
            {"role":"assistant", "content":f"{example_response_1}"},
            {"role":"user", "content":f"{example_text_2}"},
            {"role":"assistant", "content":f"{example_response_2}"},
            {"role":"user", "content":f"{example_prompt} {text}"}
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
        print(f"No Cleaned Desc, Deleting Job ID {key}")
        del data[key]
        
    if len(data[key]["cleaned_desc"]) > 1: #there are jds that seemed to contain no techs after classifier, ignore those
        # print(f"To ask_gpt: {key}")
        data[key]["techs"] = [x.lower() for x in ask_gpt(data[key]["cleaned_desc"])["choices"][0]["message"]["content"].split(", ")]
        # print(f"techs: {data[key]['techs']}")
    else:
        data[key]["techs"] = ""
        # print(f"no techs for {key}")

        
def update_tech_json(datapath="data", prefix='p-', startstr="raw_data"):
    for filename in os.listdir(datapath):
        if filename.startswith(startstr): # just with one file at first
            print(f"Processing {filename}")
            filepath = fr"{datapath}/{filename}"
            with open(filepath) as f:
                data = json.load(f)
            keylist = list(data.keys())
            print(f"There are {len(keylist)-1} jobs in {filename}")
            roughly_split = [x[-1] for x in np.array_split(np.array(keylist[:-1]), 10)]
            for key in keylist:
                # print(key)
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




# To re-use the saved model:
with open(saved_clf, "rb") as model_file:
    clf = pickle.load(model_file)
with open(saved_tfidf, "rb") as vect_file:
    tfidf_vectorizer = pickle.load(vect_file)


nlp = spacy.load("en_core_web_sm")


# Go through each un-processed raw data file and use the binary classifier to
# try to pare down the descriptions to be shorter
for filename in os.listdir("data"):
    if filename.startswith("raw_data"):
        print(f"Shortening JDs for {filename}")
        with open(fr"data/{filename}") as f:
            data = json.load(f)
        for key in list(data.keys()):
            if key.startswith("metadata"):
                continue
            elif "desc" not in data[key]: #load-in got broken, remove the job
                del data[key]
            else:
            #    print(data[key])
               try:
                cleaned_jd = check_for_techs(data[key]['desc'], tfidf_vectorizer, clf, nlp, 5)
                data[key]["cleaned_desc"] = cleaned_jd
               except Exception as e:
                #    print(data[key])
                   print(f"Error: {e}")
        data["metadata"]["models"] = {}
        data["metadata"]["models"]["classifier"] = {}
        data["metadata"]["models"]["classifier"]["clf"] = saved_clf
        data["metadata"]["models"]["classifier"]["tfidf"] = saved_tfidf
        data["metadata"]["models"]["NER"] = {}
        data["metadata"]["models"]["NER"]["model"] = gpt_model
        data["metadata"]["models"]["NER"]["prompt"] = gpt_prompt
        data["metadata"]["models"]["NER"]["examples"] = {}
        data["metadata"]["models"]["NER"]["examples"]["example_1"] = example_text_1
        data["metadata"]["models"]["NER"]["examples"]["example_response_1"] = example_response_1
        data["metadata"]["models"]["NER"]["examples"]["example_2"] = example_text_2
        data["metadata"]["models"]["NER"]["examples"]["example_response_2"] = example_response_2
        dict_to_json(data, fr"data/{filename}")
        print(f"Shortened {filename}")
    else:
        continue
print("Finished shortening JDs.")
#Now raw data jsons have cleaned descs. these are what we want to feed in to openai api
openai.api_key = api_key
print(f"Beginning tech identification")
#This line just goes through all files in os.listdir("data") which start with "raw_data", renaming the file with a "p-" prefix after.

update_tech_json("data", "p-", "raw_data")
