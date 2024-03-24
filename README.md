# jobReqs - Python, AWS, Scrapy, openAI, docker

## Table of Contents
* [General Info](#general-info)
* [indscraper](#indscraper)
* [tech_pipe](#tech_pipe)
* [gpt_pipe](#gpt_pipe)
* [To Do](#to-do)

## General Info
This project involves scraping jobs from Indeed via scrapy spiders to find trends in various data field job opportunities.  The project is currently broken up in to three sections: The scraper within indscraper, the data cleaning within tech_pipe, and the OpenAI chatGPT portion within gpt_pipe.

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

## To Do
- Publish/share PowerBI dashboard(s)
- Complete then add pytests folder from local testing
- Add terraform for remaining AWS resources (scraper, etc. on ec2)
- Add documentation for others to run end-to-end
- Create architecture diagram(s)
- Create Hugging Face training data (classifier already working, input data subpar)
- Update binary classifer - add more training data to tune further and create updated .pkl files
- Create ML workflow for classifier/ner on AWS

