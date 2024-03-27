import json
import re
import boto3
import os
import logging

## Below are reading functions if we want to use text files to store mappings
# def read_mappings(filepath):
#     mappings = {}
#     with open(filepath, 'r') as f:
#         for line in f:
#             line = line.strip()
#             if line:
#                 pattern, replacement = line.split(',', 1)
#                 mappings[pattern.strip()] = replacement.strip()
#     return mappings

# def read_exact_remove_patterns(filepath):
#     "Read the terms we want to remove, ignore empty lines if they exist"
#     with open(filepath, 'r') as f:
#         return [r'\b{}\b'.format(line.strip()) for line in f if line.strip()]

## Just hard-code them in for testing now
mappings = {
    r'\b(aws|amazon)\b': 'aws',
    r'\b(ai|artificial intelligence|contextual ai)\b': 'ai',
    r'\b(google|gcp)\b': 'google',
    r'\b(power bi|powerbi)\b': 'powerbi',
    r'\b(excel)\b':'excel',
    r'\b(microsoft word|ms word|ms office)\b':'microsoft office',
}

exact_remove_patterns = [
 '\\bskills\\b',
 '\\banalyst\\b',
 '\\bdocumentation\\b',
 '\\bprototyping tools\\b',
 '\\banalytical tools\\b',
 '\\bdata modeling\\b',
 '\\btheories\\b',
 '\\bdeep learning\\b',
 '\\bproduct owner\\b',
 '\\bprocessing\\b',
 '\\bmachine learning models\\b',
 '\\banalytics\\b',
 '\\bnone\\b',
 '\\bengineer\\b',
 '\\banalysis\\b',
 '\\bstatistical\\b',
 '\\bengineering\\b',
 '\\bvisualization\\b'
 ]

# Function to remove exactly matching strings
### Run first before mappings.  Also run partial match function before mappings
def remove_techs_exact(lst, patterns):
    # Process each string in the list
    processed_lst = []
    for string in lst:
        # Flag to indicate if the string should be removed
        remove_string = False
        # Check if any pattern matches the entire string
        for pattern in patterns:
            pattern_compiled = re.compile(pattern, flags=re.IGNORECASE)
            if pattern_compiled.search(string):
                remove_string = True
                break
        # If the string should not be removed, keep it
        if not remove_string:
            processed_lst.append(string)
    
    return processed_lst


# To map terms
def map_techs(lst, mappings):
    # Process each string in the list
    processed_lst = []
    for string in lst:
        # Flag to check if a match is found
        match_found = False
        # Apply each mapping
        for pattern, replacement in mappings.items():
            pattern_compiled = re.compile(pattern, flags=re.IGNORECASE)
            # If a match is found, substitute the entire string
            if pattern_compiled.search(string):
                string = replacement
                match_found = True
                break  # No need to check further mappings if a match is found
        # If no match is found, keep the original string
        if not match_found:
            processed_lst.append(string)
        else:
            processed_lst.append(replacement)
    
    return processed_lst




s3 = boto3.client('s3')
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']
    stripped_key = key.split("/")[-1]
    save_bucket_name = os.environ.get("SAVE_BUCKET_NAME")
    
    # s3_bucket_name = 'gpt-bucket-indeed'
    # filename_s3 = "data/indeed_27_03_2024.json"
    
    # Get the data from the event
    response = s3.get_object(Bucket=bucket, Key=key)
    content = response['Body'].read().decode('utf-8')
    lines = content.splitlines()
    
    # Get the date information from the filename
    day = stripped_key.split('_')[1]
    month = stripped_key.split('_')[2]
    year = stripped_key.split('_')[3].split('.')[0]
    
    
    # Empty bucket to hold newly cleaned data
    modified_lines = []
    # Line-by-line clean the techs via removal and mapping
    for line in lines:
        data = json.loads(line)
        
        # Add the date information first
        data['day'] = int(day)
        data['month'] = int(month)
        data['year'] = int(year)
        
        if 'cleaned_techs' in data:
            # First try to remove the techs we don't want
            try:
                data['cleaned_techs'] = remove_techs_exact(data['cleaned_techs'], exact_remove_patterns)
            except Exception as e:
                logger.warning(f"Error removing techs for line {line}: {e}")
            # Then try to map the remaining techs
            try:
                data['cleaned_techs'] = map_techs(data['cleaned_techs'], mappings)
            except Exception as e:
                logger.warning(f"Error mapping techs for line {line}: {e}")
            # Put the cleaned tech list in
            modified_lines.append(json.dumps(data))
        else: # Don't keep the line if there's no techs left
            logger.info(f"No cleaned techs in line {line}")
    # Join all the now cleaned lines back together
    modified_content = '\n'.join(modified_lines)
    # Try to save the results
    try:
        s3.put_object(Bucket=save_bucket_name, Key=key, Body=modified_content)
        logger.info(f"File {key} saved to {save_bucket_name}")
    except Exception as e:
        logger.error(f"Error saving {key} to {save_bucket_name}: {e}")
    
    ## For testing, delete after:
    return {
        'statusCode': 200,
        'body': "Sucessfully cleaned techs and saved"
    }