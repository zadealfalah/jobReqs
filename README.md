# jobReqs - Python, AWS, openAI

## Table of Contents
* [General Info](#general-info)
* [To Do](#to-do)

## General Info
This project utilizes Selenium to pull daily job data from Indeed.  The data is stored in Amazon S3 buckets as .json files and the job descriptions are analyzed with the openAI API to find skills and technologies that are sought after.  
Currently searching for remote jobs with the following keywords: "data science", "data analyst", "data engineer", "machine learning engineer", "mlops"

## To Do
- Create MWAA workflow on AWS
- Train spaCy model with openAI results
 
