import re
import json
import spacy
import pickle
import os

class TechIdentificationPipeline:
    def __init__(self, filename):
        self.filename = filename
        self.data = []
        self.nlp = spacy.load("en_core_web_sm")
        self.clf = os.
        
    def read_data_lines(self):
        """Stores each line (job) into self.data

        Args:
            filename (_type_): _description_
            data (_type_): _description_
        """
        if not self.filename:
            print(f"Error, no filename detected!")
        else:
            try:
                print(f"Parsing {self.filename} to self.data")
                with open(rf"{self.filename}") as f:
                    for line in f:
                        self.data += [json.loads(line)]
            except Exception as e:
                print(f"Error parsing {self.filename}: {e}")
            
        
        
    def select_relevant_text(self, vectorizer, clf, nlp, n=5):
        """Uses pretrained binary classifier to decide if a given section of jd is relevant to techs.  
        Used to shorted number of tokens for GPT.  Adds split jds directly to each job in self.data

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
            print(f"Data field is empty! Reading in data from {self.filename}")
            self.read_data_lines()
        
        
        print(f"Data sucessfully read in, updating jds")
        modified_data = []
        for job in self.data:
            original_jd = job['job_description']
            # Don't use split function as we don't want the output I use to label them manually.
            splits = original_jd.count("\n")//n
            split_text = re.findall("\n".join(["[^\n]+"]*splits), original_jd)
            processed = [" ".join([token.lemma_ for token in nlp(para)]) for para in split_text]
            
            transformed = vectorizer.transform(processed)
            pred_vals = clf.predict(transformed)
            
            zipped_paras = list(zip(split_text, pred_vals))
            # return(zipped_paras)
            split_jd = " ".join([text for (text, label) in zipped_paras if label == 1])
            job['split_jd'] = split_jd.strip("\n")  # add on stripping the newlines from the cleaned descs to lower # tokens
            modified_data.append(job) # Store the whole job in the modified data list
        
        print(f"Rewriting {self.filename} with updated jobs")
        with open(self.filename, 'w') as f:
            for job in modified_data:
                json.dump(job, f)
                f.write('\n')


