import boto3
import json
import os
from dotenv import load_dotenv
import asyncio
from gpt_pipeline import GptPipeline

loop = asyncio.get_event_loop()

async def fetch_gpt_funct(pipeline):
    await pipeline.fetch_gpt_techs()
    

def upload_to_s3(data, object_key):
    save_bucket_name = os.environ.get("SAVE_BUCKET_NAME")
    save_bucket_folder = os.environ.get("SAVE_FOLDER_NAME")
    try:
        json_data = json.dumps(data)
    except Exception as e:
        print(f"Error with json dump: {e}")
    
    full_object_key = f"{save_bucket_folder}/{object_key}"
    
    try:
        # Upload data to S3
        s3.put_object(
            Bucket=save_bucket_name,
            Key=full_object_key,
            Body=json_data
        )
        print(f"Data saved as {full_object_key}")
    except Exception as e:
        print(f"Error saving data to {save_bucket_name}: {e}")

load_dotenv()

s3 = boto3.client('s3')

def handler(event, context):
    
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']
    
    print(bucket)
    print(key) # This would be something like data/indeed_19_02_2024.json
    
    # Get our object
    response = s3.get_object(Bucket=bucket, Key=key)
    json_lines = response['Body'].read().decode('utf-8').splitlines()
    s3_data = [json.loads(line) for line in json_lines]
    
    pipeline = GptPipeline(filename=key, data=s3_data)
    
    print(f"Running fetch_gpt_funct with async")
    loop.run_until_complete(fetch_gpt_funct(pipeline))
    print(f"Running clean_gpt_response()")
    pipeline.clean_gpt_response()
    print(f"Running clean_tech_lists()")
    pipeline.clean_tech_lists()
    
    # Remove prefixes from original key before uploading to s3
    stripped_key = key.split("/")
    
    # Save result to new s3 bucket
    upload_to_s3(pipeline.data, stripped_key[-1])
