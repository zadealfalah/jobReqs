# jobReqs - Python, AWS, openAI

## Table of Contents
* [General Info](#general-info)
* [Main](#Main)
* [AWS](#AWS)
* [To Do](#to-do)

## General Info
This project utilizes Selenium to pull daily job data from Indeed to find the most sought after technologies for various roles, as well as the trends in job postings for each role.  The technologies are discovered through the use of the OpenAI API and spaCy.
There are two branches: a locally hosted 'main', and a version for AWS hosting 'aws_automation'.

## Main
The data is stored locally as .json files and the job descriptions are analyzed with the OpenAI API to find skills and technolgoies which are sought after in the following search terms: ["data science", "data analyst", "data engineer", "machine learning engineer", "mlops"].  To be run nightly, searching for remote jobs posted in the last 24 hours.

Job descriptions from Indeed are shortened via a binary classifier trained with spaCy.  The data used to train the model were job descriptions which were pulled, split by newlines, and labeled by hand as to if they contained technologies or not.  The binary classifier is then used on the same splits on new job descriptions to remove any portions which do not contain technologies.

Shortened job descriptions are sent into the OpenAI API using the gpt-3.5-turbo engine.  The prompt is set and given examples to allow GPT To pull lists of technologies.  

The end goal is to have this run daily, slowly building up our results.  The OpenAI API will be used to discover new technologies periodically and their results will be used to (re)train spaCy models that will be used in place of the API for the NER task of discovering technologies in the job descriptions to save on costs.  By combining these two discovery approaches, we will be able to adapt to new technologies being launched / coming in to favor, while still keeping costs low.

Once completed, this will be run as 'job_search.py' --> 'add_techs.py' --> 'check_results.py' --> 'create_hf_data.py'* --> 'hf_zero_shot.py'
*'create_hf_data.py' will be used whenever we need to refresh our model with new training data.  Will be done periodically to make sure that new techs aren't lost.

## AWS
Similar to main, except that the data are stored in Amazon S3 buckets as .json files.  Code slightly adapted to use AWS Lambda.
Currently non-operational due to cloudfare updates (as of 10/09/2023).  Cloudfare now detects Selenium as a bot and stops the search.  Can run with old data.

## To Do
- Train spaCy and TensorFlow models with OpenAI API results
- Change Selenium to allow running on AWS again
- Create visualizations of results
- Add logging instead of long metadata
- Continue prompt engineering to lower API costs
- Write DAG to alternate API vs. spaCy/TF discovery
- Tidy up, remove extra testing notebooks

