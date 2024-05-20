# jobReqs - Python, AWS, Scrapy, openAI, docker, terraform

## On Hiatus As Of 5/20/2024

![AWS Architecture Diagram](/images/aws_architecture.jpeg)

## Table of Contents
* [General Info](#general-info)
* [indscraper](#indscraper)
* [tech_pipe](#tech_pipe)
* [gpt_pipe](#gpt_pipe)
* [Last Steps](#last-steps)
* [Example Results](#example-results)
* [To Do](#to-do)
* [Hiatus](#hiatus)

## General Info
This project involves scraping jobs from Indeed via scrapy spiders to find trends in various data-based job opportunities.  The data is collected and cleaned daily via AWS and the results are visible via PowerBI.  A basic dashboard has already been created and some images from it can be seen in the [Example Results](#example-results) section.

## indscraper
This scraper was created via docker and is hosted on AWS ECR.  An AWS ECS cluster was created with a CRON scheduler to run the scraper at 00:01 UTC daily, currently scraping for remote positions with the keywords of 'data scientist', 'data analyst', and 'data engineer' on Indeed posted within the last 24 hours.
The data is scraped with Scrapy in conjuction with ScrapeOps for their proxy aggregator, and the results are saved as .jsonl to an initial AWS S3 bucket called 'scrapy-bucket-indeed'.

## tech_pipe
The tech_pipe portion of this project is an AWS Lambda function with another ECR-hosted docker image for transforming the data stored within the 'scrapy-bucket-indeed' S3 bucket.  Here a binary classifier that was created to help shorten the job descriptions by removing non-relevant paragraphs from the text is used.  This binary classifier emphasises a low number of false negatives so that more text is kept than may be necessary, but less relevant text is lost.  The Lambda function is triggered when a new .jsonl file is input to the '/data' folder within said bucket and does the following:
* Spin up tech_pipe docker image
* Read in the file from S3
* Find and read in the binary classifier .pkl files
* Transform and process every job description with said binary classifier
* Save results to a new S3 bucket called 'tech-bucket-indeed'

## gpt_pipe
The gpt_pipe picks up where the tech_pipe left off by again utilizing an ECR-hosted docker image with a Lambda trigger based on PUT commands, now to the 'tech-bucket-indeed' S3 bucket.  Here the shortened job descriptions are passed to the OpenAI API to find the relevant technologies listed within.  These API calls are done asynchronously and use chat completions with engineered prompts to properly direct the LLM in formatting our results.  Despite this, the results can sometimes be poor so some further cleaning is required.  We are also in the process of creating our own classifier via Hugging Face as it is believed we can create a more accurate, and obviously much cheaper tech classifier with some work.

## Last Steps
After the gpt_pipe is complete we do a final cleaning where some basic removal and mapping of terms is done.  This is currently via Lambda functions where the results from the OpenAI API are first removed via regex mapping if we knew a tech was incorrectly identified. For example, a common 'tech' identified was "data processing".  After this the remaining techs were mapped in cases where there were common, obvious overlaps.  For example "aws", "amazon web service", and "aws knowledge" would all be mapped to just "aws" for analysis.  
This portion of the project is necessary due to the OpenAI results and will hopefully be removable or at least reducable once a better classifier is implemented.
Once the data is as clean as we can get it, AWS Athena is used to query the results and an ODBC connection is made with PowerBI to display them.  The current PowerBI dashboard is quite basic and will be updated with proper visualizations.

## Example Results
Here is an example page of a PowerBI dashboard from our results.  Note that it is currently very basic and proper, updated visualizations will be created.
![Screenshot of a basic PowerBI Dashboard.](/images/updated_dashboard.PNG)

## To Do
- Create nice PowerBI dashboard
- Complete then add pytests folder from local testing
- Add terraform for remaining AWS resources (scraper, etc. on ec2)
- Add documentation for others to run end-to-end

## Hiatus
As of 5/20/2024 this project has been put on hiatus.  I will probably be returning to it in a few months to follow up on the above to-do lists, but it has served its purpose and ran without changes for a few months.  Future work will most likely focus on using the already collected data, or productionizing the code. 
- Create architecture diagram(s)
- Create Hugging Face training data (classifier already working, input data subpar)
- Update binary classifer - add more training data to tune further and create updated .pkl files
- Create ML workflow for classifier/ner on AWS
