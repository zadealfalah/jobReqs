import re
from typing import Dict

from ray.data import Dataset
import pandas as pd
import ray



## May want to change to be able to read in from scraper json output directly
def load_data(dataset_loc: str, num_samples: int=None) -> Dataset:
    ds = ray.data.read_csv(dataset_loc)