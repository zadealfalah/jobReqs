import re
import json
import spacy
import pickle
import os
import logging
from dotenv import load_dotenv

load_dotenv()

class TechIdentificationPipeline:
    def __init__(self, filename, data=[]):
        self.filename = filename
        self.data = data
        self.nlp = spacy.load("en_core_web_sm")
        self.clf = None # Don't read in automatically
        self.tfidf = None # Don't read in automatically
        
        ## Logging
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.INFO)

        
    def read_data_lines_from_file(self):
        """Stores each line (job) into self.data assuming data file exists

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
            self.read_data_lines_from_file()
        
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
    