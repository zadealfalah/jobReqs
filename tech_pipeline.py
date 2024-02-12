import re
import json
import spacy
import pickle
import os
import logging
from dotenv import load_dotenv
import openai
from openai import OpenAI
# import backoff
from tenacity import retry, stop_after_attempt, wait_random_exponential
import asyncio
import aiohttp
from aiohttp import ClientResponseError

load_dotenv()

class TechIdentificationPipeline:
    def __init__(self, filename):
        self.filename = filename
        self.data = []
        self.nlp = spacy.load("en_core_web_sm")
        self.clf = None
        self.tfidf = None
        
        self.logger = logging.getLogger("TechIdentificationPipeline")
        self.logger.setLevel(logging.INFO)
        file_handler = logging.FileHandler("TechIdPipeline.log")
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        self.GPT_MODEL=os.getenv("GPT_MODEL")
        self.GPT_PROMPT=os.getenv("GPT_PROMPT")
        self.EXAMPLE_TEXT_1=os.getenv("EXAMPLE_TEXT_1")
        self.EXAMPLE_RESPONSE_1=os.getenv("EXAMPLE_RESPONSE_1")
        self.EXAMPLE_TEXT_2=os.getenv("EXAMPLE_TEXT_2")
        self.EXAMPLE_RESPONSE_2=os.getenv("EXAMPLE_RESPONSE_2")
        self.EXAMPLE_PROMPT=os.getenv("EXAMPLE_PROMPT")
        
        self.system_prompt = f"{self.EXAMPLE_TEXT_1}\n{self.EXAMPLE_RESPONSE_1}\n{self.EXAMPLE_TEXT_2}\n{self.EXAMPLE_RESPONSE_2}\n"
        
    def read_data_lines(self):
        """Stores each line (job) into self.data

        Args:
            filename (_type_): _description_
            data (_type_): _description_
        """
        if not self.filename:
            self.logger.info(f"Error, no filename detected!")
        else:
            try:
                self.logger.info(f"Parsing {self.filename} to self.data")
                with open(rf"{self.filename}") as f:
                    for line in f:
                        self.data += [json.loads(line)]
            except Exception as e:
                self.logger.info(f"Error parsing {self.filename}: {e}")
            
    
    def read_in_clf(self):
        try:
            with open(fr"{os.getenv('SAVED_CLF')}", "rb") as model_file:
                self.clf = pickle.load(model_file)
            self.logger.info(f"Clf read in")
        except Exception as e:
            self.logger.info(f"Error reading in clf: {e}")
    
    def read_in_tfidf(self):
        try: 
            with open(fr"{os.getenv('SAVED_TFIDF')}", "rb") as vect_file:
                self.tfidf = pickle.load(vect_file)
            self.logger.info(f"Tfidf read in")
        except Exception as e:
            self.logger.info(f"Error reading in tfidf: {e}")
    
        
    def select_relevant_text(self, n=5):
        """Uses pretrained binary classifier to decide if a given section of jd is relevant to techs.  
        Used to shorted number of tokens for GPT.  Adds split jds directly to each job in self.data, rewrites self.filename.

        Args:
            data (list): List of jobs from read_data_lines()
            vectorizer (_type_): _description_
            clf (_type_): _description_
            nlp (_type_): _description_
            n (int, optional): Number of sections to split text in to. Defaults to 5.

        Returns:
            _type_: _description_
        """
        if self.data == []:
            self.logger.info(f"Data field is empty! Reading in data from {self.filename}")
            self.read_data_lines()
        
        if self.clf == None:
            self.logger.info(f"Clf not yet read in.  Reading in now.")
            self.read_in_clf()
            
        if self.tfidf == None:
            self.logger.info(f"Tfidf not yet read in.  Reading in now.")
            self.read_in_tfidf()
        
        
        self.logger.info(f"Data, clf, tfidf all successfuly loaded. Updating jds")
        modified_data = []
        for job in self.data:
            original_jd = job['job_description']
            # Don't use split function as we don't want the output I use to label them manually.
            splits = original_jd.count("\n")//n
            split_text = re.findall("\n".join(["[^\n]+"]*splits), original_jd)
            processed = [" ".join([token.lemma_ for token in self.nlp(para)]) for para in split_text]
            
            transformed = self.tfidf.transform(processed)
            pred_vals = self.clf.predict(transformed)
            
            zipped_paras = list(zip(split_text, pred_vals))
            # return(zipped_paras)
            split_jd = " ".join([text for (text, label) in zipped_paras if label == 1])
            job['split_jd'] = re.sub(r'\s*\n+\s*', ' ', split_jd)  # add on stripping the newlines from the cleaned descs to lower # tokens
            modified_data.append(job) # Store the whole job in the modified data list
        
        ## Replace self.data with jobs from modified_data which have techs in them after cutting
        self.data = [job for job in modified_data if len(job.get('split_jd', '')) > 1]
        
        self.logger.info(f"Rewriting {self.filename} with updated jobs")
        with open(self.filename, 'w') as f:
            for job in self.data:
                json.dump(job, f)
                f.write('\n')



    
    # @backoff.on_exception(backoff.expo, openai.RateLimitError, max_tries=6)
    @retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
    async def ask_gpt(self, split_jd):
        headers = {
            "Authorization": f"Bearer {self.OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        async with aiohttp.ClientSession(headers=headers) as session:
            try:
                async with session.post('https://api.openai.com/v1/chat/completions', json={
                    "model": self.GPT_MODEL,
                    "messages": [
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": f"{self.EXAMPLE_PROMPT} {split_jd}"}
                    ]
                }) as response:
                    return await response.json()
            except ClientResponseError as e:
                if e.status == 429:  # Rate limit exceeded error
                    logging.warning(f"Rate limit exceeded in ask_gpt method: {e}")
                    raise e
                else:
                    logging.warning(f"Unexpected error occurred in ask_gpt method: {e}")
                    raise e
            except Exception as e:
                logging.warning(f"Unexpected error occurred in ask_gpt method: {e}")
                raise e

    async def fetch_gpt_techs(self):
        self.logger.info(f"Getting techs from gpt {self.GPT_MODEL}")
        tasks = []
        for job in self.data:
            split_jd = job['split_jd']
            tasks.append(self.ask_gpt(split_jd))
        responses = await asyncio.gather(*tasks)
        for job, response in zip(self.data, responses):
            # job['gpt_response'] = [x.lower() for x in response["choices"][0]["message"]["content"].split(", ")] # Get the tech list and lowercase it
            job['gpt_response'] = response
            
        self.logger.info(f"Rewriting {self.filename} with gpt techs")
        with open(self.filename, 'w') as f:
            for job in self.data:
                json.dump(job, f)
                f.write('\n')
                
    
    def clean_gpt_response(self):
        self.logger.info(f"Cleaning gpt responses")
        for job in self.data:
            full_gpt = job['gpt_response']
            gpt_message = full_gpt['choices'][0]['message']['content']
            common_response = "Return specific tools and technologies from the following text: "
            if gpt_message.startswith("["): # Starts with a list
                job['gpt_techs'] = gpt_message.lower()
                self.logger.info(f"GPT techs {gpt_message.lower()} added to job {job['job_key']}")
            elif gpt_message.startswith(common_response): # Starts with command given
                self.logger.info(f"GPT Response includes command, cleaning")
                gpt_techs = gpt_message[len(common_response):].lower().split(", ")
                job['gpt_techs'] = gpt_techs
                self.logger.info(f"GPT techs {gpt_techs} added to job {job['job_key']}")
            else: # Some other kind of incorrect response
                self.logger.info(f"GPT Response is non-standard")
                job['gpt_techs'] = None
                self.logger.warning(f"GPT techs for {job['job_key']} non-standard, added None to gpt_techs")
                
        self.logger.info(f"Overwriting {self.filename} with updated data")
        with open(self.filename, 'w') as f:
            for job in self.data:
                json.dump(job, f)
                f.write('\n')
        self.logger.info(f"Data overwritten")