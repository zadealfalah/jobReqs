import pickle
from dotenv import load_dotenv
import os
import spacy
from utils import check_for_techs, dict_to_json, ask_gpt, update_tech_json, get_job_techs, print_attempt_number
import json
import numpy as np
import openai


load_dotenv()    

api_key = os.getenv("openai_api_key")
example_text_1 = os.getenv("example_text_1")
example_response_1 = os.getenv("example_response_1")
example_text_2 = os.getenv("example_text_2")
example_response_2 = os.getenv("example_response_2") 
saved_clf = os.getenv("saved_clf")
saved_tfidf = os.getenv("saved_tfidf")
gpt_model = os.getenv("gpt_model")
gpt_prompt = os.getenv("gpt_prompt")

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
               # print(data[key])
               try:
                cleaned_jd = check_for_techs(data[key]['desc'], tfidf_vectorizer, clf, nlp, 5)
                data[key]["cleaned_desc"] = cleaned_jd
               except Exception as e:
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
