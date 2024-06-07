import pytest

from data import CustomPreprocessor


# Currently in the classifier_model branch
# Remember to change once we merge to main to 
# https://raw.githubusercontent.com/zadealfalah/jobReqs/main/datasets/...
@pytest.fixture
def dataset_loc():
    return "https://raw.githubusercontent.com/zadealfalah/jobReqs/classifier_model/datasets/dataset.csv" 

@pytest.fixture
def preprocessor():
    return CustomPreprocessor()