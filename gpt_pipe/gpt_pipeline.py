import logging
from dotenv import load_dotenv
import os
import json
import asyncio
from openai import OpenAI, AsyncOpenAI
import re

load_dotenv()



class GptPipeline:
    def __init__(self, filename, data=[]):
        self.filename = filename
        self.data = data
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.INFO)
        
        ## Gpt
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        self.GPT_MODEL=str(os.environ.get("GPT_MODEL"))
        self.GPT_PROMPT=str(os.environ.get("GPT_PROMPT"))
        self.EXAMPLE_TEXT_1=str(os.environ.get("EXAMPLE_TEXT_1"))
        self.EXAMPLE_RESPONSE_1=str(os.environ.get("EXAMPLE_RESPONSE_1"))
        self.EXAMPLE_TEXT_2=str(os.environ.get("EXAMPLE_TEXT_2"))
        self.EXAMPLE_RESPONSE_2=str(os.environ.get("EXAMPLE_RESPONSE_2"))
        self.EXAMPLE_PROMPT=str(os.environ.get("EXAMPLE_PROMPT"))
        self.system_prompt = f"{self.EXAMPLE_TEXT_1}\n{self.EXAMPLE_RESPONSE_1}\n{self.EXAMPLE_TEXT_2}\n{self.EXAMPLE_RESPONSE_2}\n"
        self.temperature = 0.2
        
        ## Add gpt metadata to logger
        self.logger.info(f"GPT Metadata:")
        self.logger.info(f"GPT_MODEL: {self.GPT_MODEL}")
        self.logger.info(f"GPT_PROMPT: {self.GPT_PROMPT}")
        self.logger.info(f"EXAMPLE_TEXT_1: {self.EXAMPLE_TEXT_1}")
        self.logger.info(f"EXAMPLE_RESPONSE_1: {self.EXAMPLE_RESPONSE_1}")
        self.logger.info(f"EXAMPLE_TEXT_2: {self.EXAMPLE_TEXT_2}")
        self.logger.info(f"EXAMPLE_RESPONSE_2: {self.EXAMPLE_RESPONSE_2}")
        self.logger.info(f"EXAMPLE_PROMPT: {self.EXAMPLE_PROMPT}")
        self.logger.info(f"temperature: {self.temperature}")
        
        ## Cleaning
        self.term_mapping = None # Don't read in automatically
        self.terms_to_remove = None # Don't read in automatically
        
        
    async def ask_gpt_with_retry(self, split_jd, client, retry_queue):
        # Just have a 0.5s sleep here for now for testing, must remove once actual backoff implemented!
        await asyncio.sleep(0.5)  
        
        
        try:
            response = await client.chat.completions.create(
                model=self.GPT_MODEL,
                temperature=self.temperature,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": f"{self.EXAMPLE_PROMPT} {split_jd}"}
                ]
            )
            # return response.model_dump_json()
            gpt_response = response.model_dump_json()
            if "error" in response:
                self.logger.warning(
                    f"Request failed with error {gpt_response['error']}"
                )
                if "Rate limit" in response["error"].get("message", ""):
                    ### Not fully implemented.
                    await asyncio.sleep(2)
                    await retry_queue.put((split_jd, client))
            return gpt_response
        except Exception as e:
            self.logger.warning(f"Error in GPT request: {e}")
            raise


    async def fetch_gpt_techs(self):
        async_client = AsyncOpenAI(api_key=self.OPENAI_API_KEY, max_retries=5)
        # print(f"Async client type: {type(async_client)}")
        tasks = []
        retry_queue = asyncio.Queue() ### Not fully implemented
        
        # async def retry_worker():
        #     while True:
        #         split_jd, client = await retry_queue.get()
        #         await self.ask_gpt_with_retry(split_jd, client, retry_queue)
        #         retry_queue.task_done()
                
        # retry_worker_task = asyncio.create_task(retry_worker())
        modified_data = []
        for job in self.data:
            split_jd = job['split_jd']
            tasks.append(self.ask_gpt_with_retry(split_jd, client=async_client, retry_queue=retry_queue))
        responses = await asyncio.gather(*tasks)
        for job, response in zip(self.data, responses):
            job['gpt_response'] = response
            modified_data.append(job)
            
        ## Replace self.data with jobs from modified_data which have the tech lists
        self.data = [job for job in modified_data]

        ## Was for local use, not for aws implementation        
        # self.logger.info(f"Rewriting {self.filename} with gpt techs")
        # with open(self.filename, 'w') as f:
        #     for job in self.data:
        #         json.dump(job, f)
        #         f.write('\n')
                
                
    
    def clean_gpt_response(self):
        self.logger.info(f"Cleaning gpt responses")
        modified_data = []
        for job in self.data:
            full_gpt = job['gpt_response']
            
            try:
                gpt_message = json.loads(full_gpt)['choices'][0]['message']['content'].strip().replace('\n', '')
            except TypeError as e:
                self.logger.warning(f"TypeError: {e}")
                self.logger.warning(f"TypeError with gpt_message, response was: {job['gpt_response']}")
                self.logger.warning(f"Response type was: {type(job['gpt_response'])}")
                gpt_message = "Error loading gpt_message in clean_gpt_response"
                
            common_response = "Return specific tools and technologies from the following text:"
            if (gpt_message.startswith("\"[") | gpt_message.startswith("[")): # Starts with a list
                job['gpt_techs'] = gpt_message.lower().strip()
                # self.logger.info(f"GPT techs {gpt_message.lower()} added to job {job['job_key']}")
            elif gpt_message.startswith(common_response): # Starts with command given
                self.logger.info(f"GPT Response includes command, cleaning")
                gpt_techs = gpt_message[len(common_response):].lower().split(", ")
                job['gpt_techs'] = gpt_techs
                # self.logger.info(f"GPT techs {gpt_techs} added to job {job['job_key']}")
            
            
            #### Would set to None in full code, for now set to keep string with error in front
            else: # Some other kind of incorrect response
                job['gpt_techs'] = f"ERRORED! {gpt_message}"
                self.logger.warning(f"GPT techs for {job['job_key']} non-standard, added None to gpt_techs")
                self.logger.warning(f"GPT response was: {gpt_message}")
                self.logger.warning(f"GPT response type: {type(gpt_message)}")

            modified_data.append(job)
            
        ## Replace self.data with jobs from modified_data which have techs
        self.data = [job for job in modified_data]
        
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
                self.logger.warning("classifier_models folder not found")
        except Exception as e:
            self.logger.warning(f"Error reading in cleaning data: {e}")          


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

        modified_data = []
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
            modified_data.append(job)
            # self.logger.info(f"Added cleaned techs to job {job['job_key']}")
                ## Replace self.data with jobs from modified_data which have techs
        self.data = [job for job in modified_data]
    