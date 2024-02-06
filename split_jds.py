import re
import json
import spacy
import pickle
import os
import logging
from dotenv import load_dotenv
from openai import OpenAI
from openai.error import RateLimitError
import backoff
import asyncio
import aiohttp

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
            job['split_jd'] = split_jd.strip("\n")  # add on stripping the newlines from the cleaned descs to lower # tokens
            modified_data.append(job) # Store the whole job in the modified data list
        
        ## Replace self.data with jobs from modified_data which have techs in them after cutting
        self.data = [job for job in modified_data if len(job.get('split_jd', '')) > 1]
        
        self.logger.info(f"Rewriting {self.filename} with updated jobs")
        with open(self.filename, 'w') as f:
            for job in self.data:
                json.dump(job, f)
                f.write('\n')


    @backoff.on_exception(backoff.expo, aiohttp.ClientResponseError, max_tries=6)
    async def ask_gpt(self, split_jd):
        async with aiohttp.ClientSession() as session:
            async with session.post('https://api.openai.com/v1/chat/completions', json={
                "model": self.GPT_MODEL,  # Choose your model
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": f"{self.EXAMPLE_PROMPT} {split_jd}"}
                ]
            }) as response:
                return await response.json()

    async def get_techs_from_gpt(self):
        tasks = []
        for job in self.data:
            split_jd = job['split_jd']
            tasks.append(self.ask_gpt(split_jd))
        responses = await asyncio.gather(*tasks)
        for job, response in zip(self.data, responses):
            job['gpt_response'] = response