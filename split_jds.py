import re

class TechIdentificationPipeline:
    def __init__(self, filename):
        self.filename = filename
    
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
    
    