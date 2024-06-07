import re
from typing import Dict, Tuple, List

from ray.data import Dataset
import pandas as pd
import ray
from sklearn.model_selection import train_test_split
import numpy as np

from transformers import BertTokenizer

from config import STOPWORDS


## May want to change to be able to read in from scraper json output directly
## random_shuffle doesn't need seed kwarg as we have utils.set_seeds()
def load_data(dataset_loc: str, num_samples: int = None) -> Dataset:
    ds = ray.data.read_csv(dataset_loc)
    ds = ds.random_shuffle()
    ds = ray.data.from_items(ds.take(num_samples)) if num_samples else ds
    return ds


def stratify_split(ds: Dataset, stratify: str, test_size: float, shuffle: bool = True, seed: int = 5555) -> Tuple[Dataset, Dataset]:

    def _add_split(df: pd.DataFrame) -> pd.DataFrame:
        train, test = train_test_split(df, test_size=test_size, shuffle=shuffle, random_state=seed)
        train["_split"] = "train"
        test["_split"] = "test"
        return pd.concat([train, test])

    def _filter_split(df: pd.DataFrame, split: str) -> pd.DataFrame:
        return df[df["_split"] == split].drop("_split", axis=1)

    # Train, test split w/ stratify
    grouped = ds.groupby(stratify).map_groups(_add_split, batch_format="pandas")
    train_ds = grouped.map_batches(_filter_split, fn_kwargs={"split": "train"}, batch_format="pandas")
    test_ds = grouped.map_batches(_filter_split, fn_kwargs={"split": "test"}, batch_format="pandas")

    # Shuffle splits
    train_ds = train_ds.random_shuffle(seed=seed)
    test_ds = test_ds.random_shuffle(seed=seed)

    return train_ds, test_ds


def clean_text(text: str, stopwords: List = STOPWORDS) -> str:

    # Lowercase words
    text = text.lower()

    # Remove stopwords, replace with spaces
    pattern = re.compile(r"\b(" + r"|".join(stopwords) + r")\b\s*")
    text = pattern.sub(" ", text)

    # Spacing and filters
    text = re.sub(r"([!\"'#$%&()*\+,-./:;<=>?@\\\[\]^_`{|}~])", r" \1 ", text)  # add spacing around punctuation
    text = re.sub("[^A-Za-z0-9]+", " ", text)  # remove non alphanumeric chars
    text = re.sub(" +", " ", text)  # remove multiple spaces
    text = text.strip()  # strip white space at the ends
    text = re.sub(r"http\S+", "", text)  # remove links

    return text


def tokenize(batch: Dict, pretrained: str = "allenai/scibert_scivocab_uncased") -> Dict:

    tokenizer = BertTokenizer.from_pretrained(pretrained, return_dict=False)
    encoded_inputs = tokenizer(batch["text"].tolist(), return_tensors="np", padding="longest")
    return dict(ids=encoded_inputs["input_ids"], masks=encoded_inputs["attention_mask"], targets=np.array(batch["tag"]))


def preprocess(df: pd.DataFrame, class_to_index: Dict = None) -> Dict:

    df["text"] = df["jd_part"]  # Just rename the jd_parts to text
    df["text"] = df.text.apply(clean_text)
    df = df.drop(columns=["job_key"], errors="ignore")

    # Only map if we have tags already, right now have it stored as 0/1 so not needed
    # May change to store with class tags themselves later, esp. if we add more classes
    if class_to_index:
        df["tag"] = df["tag"].map(class_to_index)

    df = df[["text", "tag"]]  # reorder cols
    outputs = tokenize(df)
    return outputs


# Use in case we want tag names by default instead of the 0/1 which we have atm.
def replace_tags(df: pd.DataFrame, mapping: Dict = {0: "other", 1: "tech"}, col_name: str = "tag") -> pd.DataFrame:
    df[col_name] = df[col_name].replace(mapping)
    return df


# Would be useful to set tag names by default in case I decide to add more classes later - make a function for it
# Defined above as 'replace_tags'
class CustomPreprocessor:

    def __init__(self, class_to_index={}):
        self.class_to_index = class_to_index or {}
        self.index_to_class = {v: k for k, v in self.class_to_index.items()}

    def fit(self, ds, change_tags: bool = False):

        if change_tags:
            ds.map_batches(replace_tags)  # just use the default fn kwargs for now

        tags = ds.unique(column="tag")
        self.class_to_index = {tag: i for i, tag in enumerate(tags)}
        self.index_to_class = {v: k for k, v in self.class_to_index.items()}
        return self

    def transform(self, ds):
        return ds.map_batches(preprocess, fn_kwargs={"class_to_index": self.class_to_index}, batch_format="pandas")
