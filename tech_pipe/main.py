from tech_pipeline import TechIdentificationPipeline
import boto3
import json
import os
import asyncio
from dotenv import load_dotenv


load_dotenv()
s3 = boto3.client('s3')

loop = asyncio.get_event_loop()

async def fetch_gpt_funct(pipeline):
    await pipeline.fetch_gpt_techs()
 

def upload_to_s3(data, object_key):
    save_bucket_name = os.environ.get("SAVE_BUCKET_NAME")
    save_bucket_folder = os.environ.get("SAVE_FOLDER_NAME")
    try:
        json_data = json.dumps(data)
    except Exception as e:
        print(f"Error with json dump")
    
    full_object_key = f"{save_bucket_folder}/{object_key}"
    
    try:
        # Upload data to S3
        s3.put_object(
            Bucket=save_bucket_name,
            Key=full_object_key,
            Body=json_data
        )
        print(f"Data saved to {save_bucket_name}")
    except Exception as e:
        print(f"Error saving data to {save_bucket_name}")

def handler(event, context):

    # Get bucket and file name
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']
    
    print(bucket)
    print(key)
    
    # Get our object
    response = s3.get_object(Bucket=bucket, Key=key)
    
    json_lines = response['Body'].read().decode('utf-8').splitlines()
    s3_data = [json.loads(line) for line in json_lines]

    pipeline = TechIdentificationPipeline(filename=key, data=s3_data)
    
    pipeline.read_in_cleaning()
    pipeline.select_relevant_text()
    
    # # Testing for async within handler
    # loop = asyncio.new_event_loop()
    # asyncio.set_event_loop(loop)
    # loop.run_until_complete(fetch_gpt_funct(event, context, pipeline))
    
    print(f"Running fetch_gpt_funct with async")
    # asyncio.run(pipeline.fetch_gpt_funct())
    # loop.run_until_complete(fetch_gpt_funct)
    loop.run_until_complete(fetch_gpt_funct(pipeline))
    
    
    
    print(f"Running clean_gpt_response()")
    pipeline.clean_gpt_response()
    print(f"Running clean_tech_lists()")
    pipeline.clean_tech_lists()
    
    # Save result to new s3 bucket
    upload_to_s3(pipeline.data, key)
