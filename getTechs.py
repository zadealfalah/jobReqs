import json
import openai
from dotenv import load_dotenv
import os
from collections import Counter, defaultdict
import datetime

load_dotenv()
api_key = os.getenv("openai_api_key")
example_text_1 = os.getenv("example_text_1")
example_text_2 = os.getenv("example_text_2")

def get_techs(text):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role":"system", "content":"You identify specific technology names from job descriptions.  Respond only with a list of the names of the specific technologies."},
            {"role":"user", "content":f"Identify the specific technologies in the following text and respond with them in a list: {example_text_1}"},
            {"role":"assistant", "content":"llama 2, python, pytorch"},
            {"role":"user", "content":f"Identify the specific technologies in the following text: {example_text_2}"},
            {"role":"assistant", "content":"python, spark, sql, snowflake, tableau, aws, azure, power bi"},
            {"role":"user", "content":f"Identify the specific technologies in the following text: {text}"}
        ]
    )
    return response

def get_tech_counter(filepath):
    global tech_counter
    f = open(filepath)
    data = json.load(f)
    for key in list(data.keys()):
        job_desc = data[key]['desc']
        response = get_techs(job_desc) # keep whole object in case I want metadata from it later
        response_list = [x.lower() for x in response["choices"][0]["message"]["content"].split(", ")]
        data[key]['techs'] = response_list
        
        for term in data[key]['terms']:
            for tech in data[key]['techs']:
                tech_counter[term][tech] += 1
                
    #must bring dict_to_json to a utils file or something
    #do so when I move all my functions around
    # add a c- to filepath to indicate it's been parsed with a counter now
    dict_to_json(data, f"c-{filepath}") 
    
def counter_to_dict(counter):
    """Used after get_tech_counter to return a dict for better json storage

    Args:
        counter (_type_): _description_

    Returns:
        _type_: _description_
    """
    for key in counter.keys():
        counter[key] = dict(counter[key])
    return dict(counter)


tech_counter = defaultdict(Counter)


#Don't think I can thread this because of the counters.
for filename in os.listdir("data"):
    if filename.startswith("c-"): #already been counted
        continue
    else:
        filepath = fr"data/{filename}"
        get_tech_counter(filename)
    
tech_dict = counter_to_dict(tech_counter)

date_str = datetime.datetime.now().strftime('%d-%m-%y')

counter_dict_file_name = f"{date_str}-tech_counts"
dict_to_json(tech_dict, counter_dict_file_name)
