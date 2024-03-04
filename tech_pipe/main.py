from tech_pipeline import TechIdentificationPipeline
import boto3
import json
import os
from dotenv import load_dotenv


load_dotenv()
s3 = boto3.client('s3')


def upload_to_s3(data, object_key):
    save_bucket_name = os.environ.get("SAVE_BUCKET_NAME")
    save_bucket_folder = os.environ.get("SAVE_FOLDER_NAME")
    
    full_object_key = f"{save_bucket_folder}/{object_key}"
    
    try:
        # Upload data to S3
        s3.put_object(
            Bucket=save_bucket_name,
            Key=full_object_key,
            Body='\n'.join(json.dumps(line) for line in data)
        )
        print(f"Data saved as {full_object_key} in {save_bucket_name}")
    except Exception as e:
        print(f"Error saving data to {save_bucket_name}: {e}")

def handler(event, context):

    
    
    # Get bucket and file name
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']
    
    print(bucket)
    print(key) # This would be something like data/indeed_19_02_2024.json
    
    # Get our object
    response = s3.get_object(Bucket=bucket, Key=key)
    
    print(f"Reading in json lines")
    json_lines = response['Body'].read().decode('utf-8').splitlines()
    s3_data = [json.loads(line) for line in json_lines]
    print(f"Prepping tech ID pipeline")
    pipeline = TechIdentificationPipeline(filename=key, data=s3_data)
    print(f"selecting relevant text")
    pipeline.select_relevant_text()
    
    print(f"stripping key from {key} to {key.split('/')}")
    # Remove prefixes from original key before uploading to s3
    stripped_key = key.split("/")
    
    # Save result to new s3 bucket
    print(f"uploading to s3")
    upload_to_s3(pipeline.data, stripped_key[-1])
