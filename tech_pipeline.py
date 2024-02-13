import re
import json
import spacy
import pickle
import os
import logging
from dotenv import load_dotenv
import openai
from openai import OpenAI, AsyncOpenAI
# import backoff
# from tenacity import AsyncRetrying, RetryError, stop_after_attempt, wait_random_exponential
import asyncio
import aiohttp
from aiohttp import ClientResponseError

load_dotenv()

class TechIdentificationPipeline:
    def __init__(self, filename):
        self.filename = filename
        self.data = []
        self.nlp = spacy.load("en_core_web_sm")
        self.clf = None # Don't read in automatically
        self.tfidf = None # Don't read in automatically
        
        ## Logging
        self.logger = logging.getLogger("TechIdentificationPipeline")
        self.logger.setLevel(logging.INFO)
        file_handler = logging.FileHandler(f"{self.filename}_pipeline.log")
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        ## Gpt
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        self.GPT_MODEL=os.getenv("GPT_MODEL")
        self.GPT_PROMPT=os.getenv("GPT_PROMPT")
        self.EXAMPLE_TEXT_1=os.getenv("EXAMPLE_TEXT_1")
        self.EXAMPLE_RESPONSE_1=os.getenv("EXAMPLE_RESPONSE_1")
        self.EXAMPLE_TEXT_2=os.getenv("EXAMPLE_TEXT_2")
        self.EXAMPLE_RESPONSE_2=os.getenv("EXAMPLE_RESPONSE_2")
        self.EXAMPLE_PROMPT=os.getenv("EXAMPLE_PROMPT")
        self.system_prompt = f"{self.EXAMPLE_TEXT_1}\n{self.EXAMPLE_RESPONSE_1}\n{self.EXAMPLE_TEXT_2}\n{self.EXAMPLE_RESPONSE_2}\n"
        self.async_client = None
        
        ## Cleaning
        self.term_mapping = None # Don't read in automatically
        self.terms_to_remove = None # Don't read in automatically
        
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
            
    ###### Should add something to allow choices between various saved clf/tfidfs by version number.  Not needed for now
    def read_in_clf(self):
        try:
            for root, dirs, files in os.walk('.'):
                if 'classifier_models' in dirs:
                    c_models_folder = os.path.join(root, 'classifier_models')
                    self.logger.info("classifier_models folder found")
                    for filename in os.listdir(c_models_folder):
                        if filename.startswith("job_desc_classifier_"):
                            filepath = os.path.join(c_models_folder, filename)
                            with open(filepath, "rb") as model_file:
                                self.clf = pickle.load(model_file)
                                self.logger.info("Classifier loaded")
                            return  # Exit the function after loading the classifier
                    else:
                        self.logger.error("No classifier file found in classifier_models folder")
                        return
            else:
                self.logger.error("classifier_models folder not found")
        except Exception as e:
            self.logger.error(f"Error reading in clf: {e}")
    
    def read_in_tfidf(self):
        try:
            for root, dirs, files in os.walk('.'):
                if 'classifier_models' in dirs:
                    c_models_folder = os.path.join(root, 'classifier_models')
                    self.logger.info("classifier_models folder found")
                    for filename in os.listdir(c_models_folder):
                        if filename.startswith("job_desc_tfidf_vectorizer_"):
                            filepath = os.path.join(c_models_folder, filename)
                            with open(filepath, "rb") as model_file:
                                self.tfidf = pickle.load(model_file)
                                self.logger.info("Tfidf loaded")
                            return  # Exit the function after loading the classifier
                    else:
                        self.logger.error("No tfidf file found in classifier_models folder")
                        return
            else:
                self.logger.error("classifier_models folder not found")
        except Exception as e:
            self.logger.error(f"Error reading in tfidf: {e}")
    
    
        
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
        
        self.logger.info(f"Rewriting {self.filename} with relevant job descriptions")
        with open(self.filename, 'w') as f:
            for job in self.data:
                json.dump(job, f)
                f.write('\n')
    
    # class RateLimitError(Exception):
    #     pass
    
    # def log_attempt_number(self, retry_state):
    #     self.logger.warning(f"Retrying GPT: {retry_state.attempt_number}...")
    async def ask_gpt_with_retry(self, split_jd):
        retry_count = 0
        while True:
            try:
                response = await self.async_client.chat.completions.create(
                    model=self.GPT_MODEL,
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": f"{self.EXAMPLE_PROMPT} {split_jd}"}
                    ]
                )
                return response.json()
            except Exception as e:
                self.logger.warning(f"Error in gpt, retry #: {retry_count}")
                retry_count += 1
                if retry_count >= 6:
                    raise e

    async def fetch_gpt_techs(self):
        self.async_client = AsyncOpenAI(api_key=self.OPENAI_API_KEY)
        tasks = []
        for job in self.data:
            split_jd = job['split_jd']
            tasks.append(self.ask_gpt_with_retry(split_jd))
        responses = await asyncio.gather(*tasks)
        for job, response in zip(self.data, responses):
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
            gpt_message = json.loads(full_gpt)['choices'][0]['message']['content'].strip().replace('\n', '')
            common_response = "Return specific tools and technologies from the following text:"
            if gpt_message.startswith("["): # Starts with a list
                job['gpt_techs'] = gpt_message.lower().strip()
                # self.logger.info(f"GPT techs {gpt_message.lower()} added to job {job['job_key']}")
            elif gpt_message.startswith(common_response): # Starts with command given
                self.logger.info(f"GPT Response includes command, cleaning")
                gpt_techs = gpt_message[len(common_response):].lower().split(", ")
                job['gpt_techs'] = gpt_techs
                # self.logger.info(f"GPT techs {gpt_techs} added to job {job['job_key']}")
            else: # Some other kind of incorrect response
                job['gpt_techs'] = None
                self.logger.warning(f"GPT techs for {job['job_key']} non-standard, added None to gpt_techs")
                self.logger.warning(f"GPT response was: {gpt_message}")
                
        self.logger.info(f"Overwriting {self.filename} with updated data")
        with open(self.filename, 'w') as f:
            for job in self.data:
                json.dump(job, f)
                f.write('\n')
        self.logger.info(f"Data overwritten")
        
        
    ## Cleaning tech list section
    def read_in_cleaning(self):
        try:
            for root, dirs, files in os.walk('.'):
                if 'cleaning_resources' in dirs:
                    clean_folder = os.path.join(root, 'cleaning_resources')
                    self.logger.info("cleaning_resources folder found")
                    term_mapping_found = False
                    terms_to_remove_found = False
                    for filename in os.listdir(clean_folder):
                        if filename.startswith("term_mapping"):
                            filepath = os.path.join(clean_folder, filename)
                            with open(filepath, "rb") as file:
                                self.term_mapping = json.load(file)
                                term_mapping_found = True
                        elif filename.startswith("terms_to_remove"):
                            filepath = os.path.join(clean_folder, filename)
                            with open(filepath, "rb") as file:
                                self.terms_to_remove = json.load(file)
                                terms_to_remove_found = True
                                
                    if term_mapping_found:
                        self.logger.info("Term mapping loaded")
                    else:
                        self.logger.warning("Error loading term mapping")
                    if terms_to_remove_found:
                        self.logger.info("Terms to remove loaded")
                    else:
                        self.logger.warning("Error loading terms to remove")
                    return
                    
            else:
                self.logger.error("classifier_models folder not found")
        except Exception as e:
            self.logger.error(f"Error reading in cleaning data: {e}")          


    def map_term(self, tech, term_mapping):
        for key, mapped_terms in term_mapping.items():
            for mapped_term in mapped_terms:
                if re.match(r'\b' + re.escape(mapped_term) + r'\b', tech, re.I):
                    return key
        return tech

    def should_remove_partial(self, tech, to_remove):
        tech_lower = tech.lower()
        for keyword in to_remove:
            if re.search(r'\b' + re.escape(keyword) + r'\b', tech_lower, re.I):
                return True
        return False

    def should_remove_exact(self, tech, to_remove):
        tech_lower = tech.lower()
        for keyword in to_remove:
            if tech_lower == keyword.lower():
                return True
        return False


    def clean_tech_lists(self):
        if (self.term_mapping == None) | (self.terms_to_remove == None):
            self.logger.info(f"No cleaning resources available, loading in now")
            self.read_in_cleaning()
    
        self.logger.info(f"Cleaning gpt tech lists with cleaning resources")
        for job in self.data:
            gpt_tech_list = job['gpt_techs']
            if gpt_tech_list: # At least 1 tech listed
                cleaned_techs = []
                unique_techs = set() # Mapping ['aws glue', 'aws kinesis'] would give two ['aws'], so we want the uniques
                # print(f"{job['job_key']}, {gpt_tech_list}")
                for tech in gpt_tech_list:
                    if not self.should_remove_exact(tech, self.terms_to_remove['to_remove_exact']) and not self.should_remove_partial(tech, self.terms_to_remove['to_remove_partial']):
                        mapped_term = self.map_term(tech, self.term_mapping)
                        if mapped_term not in unique_techs:
                            unique_techs.add(mapped_term)
                            cleaned_techs.append(mapped_term)
                        else:
                            continue
                    else:
                        continue
            else:
                continue
            job['cleaned_techs'] = cleaned_techs
        self.logger.info(f"Added leaned techs to job {job['job_key']}")