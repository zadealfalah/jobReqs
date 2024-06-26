import boto3
import json
import os
from dotenv import load_dotenv
import asyncio
import logging

import aiohttp  # for making API calls concurrently
import json  # for saving results to a jsonl file
import logging  # for logging rate limit warnings and other messages
import os  # for reading API key
import re  # for matching endpoint from request URL
import tiktoken  # for counting tokens
import time  # for sleeping after rate limit is hit
from dataclasses import (
    dataclass,
    field,
)  # for storing API inputs, outputs, and metadata

import tempfile # for saving locally before transformations


load_dotenv()

s3 = boto3.client('s3')

logger = logging.getLogger()
logger.setLevel(logging.INFO)


async def process_api_requests_from_file(
    requests_filepath: str,
    save_filepath: str,
    request_url: str,
    api_key: str,
    max_requests_per_minute: float,
    max_tokens_per_minute: float,
    token_encoding_name: str,
    max_attempts: int,
    gpt_model: str,
    gpt_init_prompt: str,
    gpt_example_1: str,
    gpt_response_1: str,
    gpt_example_2: str,
    gpt_response_2: str,
    gpt_question: str,
    gpt_temp: float
):
    """Processes API requests in parallel, throttling to stay under rate limits."""
    # constants
    seconds_to_pause_after_rate_limit_error = 15
    seconds_to_sleep_each_loop = (
        0.001  # 1 ms limits max throughput to 1,000 requests per second
    )


    # infer API endpoint and construct request header
    api_endpoint = api_endpoint_from_url(request_url)
    request_header = {"Authorization": f"Bearer {api_key}"}
    # use api-key header for Azure deployments
    if "/deployments" in request_url:
        request_header = {"api-key": f"{api_key}"}

    # initialize trackers
    queue_of_requests_to_retry = asyncio.Queue()
    task_id_generator = (
        task_id_generator_function()
    )  # generates integer IDs of 0, 1, 2, ...
    status_tracker = (
        StatusTracker()
    )  # single instance to track a collection of variables
    next_request = None  # variable to hold the next request to call

    # initialize available capacity counts
    available_request_capacity = max_requests_per_minute
    available_token_capacity = max_tokens_per_minute
    last_update_time = time.time()

    # initialize flags
    file_not_finished = True  # after file is empty, we'll skip reading it
    logging.debug(f"Initialization complete.")

    # initialize file reading
    with open(requests_filepath) as file:
        # `requests` will provide requests one at a time
        requests = file.__iter__()
        logging.debug(f"File opened. Entering main loop")
        async with aiohttp.ClientSession() as session:  # Initialize ClientSession here
            while True:
                # get next request (if one is not already waiting for capacity)
                if next_request is None:
                    if not queue_of_requests_to_retry.empty():
                        next_request = queue_of_requests_to_retry.get_nowait()
                        logging.debug(
                            f"Retrying request {next_request.task_id}: {next_request}"
                        )
                    elif file_not_finished:
                        try:
                            # get new request
                            request_json = json.loads(next(requests))
                            json_payload = {
                                'model':gpt_model,
                                'messages': [
                                    {"role":"system", "content":f"{gpt_init_prompt}"},
                                    {"role":"user", "content":f"{gpt_example_1}"},
                                    {"role":"assistant", "content":f"{gpt_response_1}"},
                                    {"role":"user", "content":f"{gpt_example_2}"},
                                    {"role":"assistant", "content":f"{gpt_response_2}"},
                                    {"role":"user", "content":f"{gpt_question} {request_json['split_jd']}"}
                                ],
                                'temperature': gpt_temp
                            }
                            next_request = APIRequest(
                                task_id=next(task_id_generator),
                                request_json=request_json,
                                json_payload=json_payload,
                                token_consumption=num_tokens_consumed_from_request(
                                    request_json, api_endpoint, token_encoding_name, json_payload
                                ),
                                attempts_left=max_attempts,
                                metadata=request_json.pop("metadata", None),
                            )
                            status_tracker.num_tasks_started += 1
                            status_tracker.num_tasks_in_progress += 1
                            logging.debug(
                                f"Reading request {next_request.task_id}: {next_request}"
                            )
                        except StopIteration:
                            # if file runs out, set flag to stop reading it
                            logging.debug("Read file exhausted")
                            file_not_finished = False

                # update available capacity
                current_time = time.time()
                seconds_since_update = current_time - last_update_time
                available_request_capacity = min(
                    available_request_capacity
                    + max_requests_per_minute * seconds_since_update / 60.0,
                    max_requests_per_minute,
                )
                available_token_capacity = min(
                    available_token_capacity
                    + max_tokens_per_minute * seconds_since_update / 60.0,
                    max_tokens_per_minute,
                )
                last_update_time = current_time

                # if enough capacity available, call API
                if next_request:
                    next_request_tokens = next_request.token_consumption
                    if (
                        available_request_capacity >= 1
                        and available_token_capacity >= next_request_tokens
                    ):
                        # update counters
                        available_request_capacity -= 1
                        available_token_capacity -= next_request_tokens
                        next_request.attempts_left -= 1

                        # call API
                        asyncio.create_task(
                            next_request.call_api(
                                session=session,
                                request_url=request_url,
                                request_header=request_header,
                                retry_queue=queue_of_requests_to_retry,
                                save_filepath=save_filepath,
                                status_tracker=status_tracker,
                            )
                        )
                        next_request = None  # reset next_request to empty

                # if all tasks are finished, break
                if status_tracker.num_tasks_in_progress == 0:
                    break

                # main loop sleeps briefly so concurrent tasks can run
                await asyncio.sleep(seconds_to_sleep_each_loop)

                # if a rate limit error was hit recently, pause to cool down
                seconds_since_rate_limit_error = (
                    time.time() - status_tracker.time_of_last_rate_limit_error
                )
                if (
                    seconds_since_rate_limit_error
                    < seconds_to_pause_after_rate_limit_error
                ):
                    remaining_seconds_to_pause = (
                        seconds_to_pause_after_rate_limit_error
                        - seconds_since_rate_limit_error
                    )
                    await asyncio.sleep(remaining_seconds_to_pause)
                    # ^e.g., if pause is 15 seconds and final limit was hit 5 seconds ago
                    logging.warn(
                        f"Pausing to cool down until {time.ctime(status_tracker.time_of_last_rate_limit_error + seconds_to_pause_after_rate_limit_error)}"
                    )

        # after finishing, log final status
        logging.info(
            f"""Parallel processing complete. Results saved to {save_filepath}"""
        )
        if status_tracker.num_tasks_failed > 0:
            logging.warning(
                f"{status_tracker.num_tasks_failed} / {status_tracker.num_tasks_started} requests failed. Errors logged to {save_filepath}."
            )
        if status_tracker.num_rate_limit_errors > 0:
            logging.warning(
                f"{status_tracker.num_rate_limit_errors} rate limit errors received. Consider running at a lower rate."
            )


# dataclasses


@dataclass
class StatusTracker:
    """Stores metadata about the script's progress. Only one instance is created."""

    num_tasks_started: int = 0
    num_tasks_in_progress: int = 0  # script ends when this reaches 0
    num_tasks_succeeded: int = 0
    num_tasks_failed: int = 0
    num_rate_limit_errors: int = 0
    num_api_errors: int = 0  # excluding rate limit errors, counted above
    num_other_errors: int = 0
    time_of_last_rate_limit_error: int = 0  # used to cool off after hitting rate limits


@dataclass
class APIRequest:
    """Stores an API request's inputs, outputs, and other metadata. Contains a method to make an API call."""

    task_id: int
    request_json: dict
    json_payload: dict
    token_consumption: int
    attempts_left: int
    metadata: dict
    result: list = field(default_factory=list)

    async def call_api(
        self,
        session: aiohttp.ClientSession,
        request_url: str,
        request_header: dict,
        retry_queue: asyncio.Queue,
        save_filepath: str,
        status_tracker: StatusTracker,
    ):
        """Calls the OpenAI API and saves results."""
        logging.info(f"Starting request #{self.task_id}")
        error = None
        try:
            async with session.post(
                url=request_url, headers=request_header, json=self.json_payload
            ) as response:
                response = await response.json()
            if "error" in response:
                logging.warning(
                    f"Request {self.task_id} failed with error {response['error']}"
                )
                status_tracker.num_api_errors += 1
                error = response
                if "Rate limit" in response["error"].get("message", ""):
                    status_tracker.time_of_last_rate_limit_error = time.time()
                    status_tracker.num_rate_limit_errors += 1
                    status_tracker.num_api_errors -= (
                        1  # rate limit errors are counted separately
                    )

        except (
            Exception
        ) as e:  # catching naked exceptions is bad practice, but in this case we'll log & save them
            logging.warning(f"Request {self.task_id} failed with Exception {e}")
            status_tracker.num_other_errors += 1
            error = e
        if error:
            self.result.append(error)
            if self.attempts_left:
                retry_queue.put_nowait(self)
            else:
                logging.error(
                    f"Request {self.request_json} failed after all attempts. Saving errors: {self.result}"
                )
                # data = (
                #     [self.request_json, [str(e) for e in self.result], self.metadata]
                #     if self.metadata
                #     else [self.request_json, [str(e) for e in self.result]]
                # )
                data = self.request_json.copy()
                data.update({"result":[str(e) for e in self.result]})
                
                append_to_jsonl(data, save_filepath)
                status_tracker.num_tasks_in_progress -= 1
                status_tracker.num_tasks_failed += 1
        else:
            cleaned_techs = clean_gpt_list(response)
            
            data = self.request_json.copy()
            data.update(response)  # Add the gpt response to data
            data.update({"cleaned_techs" : cleaned_techs}) # Add the cleaned tech list to the data
            
            append_to_jsonl(data, save_filepath)
            status_tracker.num_tasks_in_progress -= 1
            status_tracker.num_tasks_succeeded += 1
            logging.debug(f"Request {self.task_id} saved to {save_filepath}")


# functions

def clean_gpt_list(response):
    possible_list = response['choices'][0]['message']['content']
    if possible_list.startswith('['): # It is a list
        try:
            stripped_list = possible_list.strip('[]')
            cleaned_list = [item.strip() for item in stripped_list.split(',')]
        except Exception as e:
            logging.warning(f"Error with response: {response}")
            logging.warning(f"Error separating {possible_list}. Returning empty list.")
            cleaned_list = []
    else: # Improperly formatted
        logging.warning(f"Error with response: {response}")
        logging.warning(f"Message {possible_list} improperly formatted. Returning empty list.")
        cleaned_list = []
    return cleaned_list


def api_endpoint_from_url(request_url):
    """Extract the API endpoint from the request URL."""
    match = re.search("^https://[^/]+/v\\d+/(.+)$", request_url)
    if match is None:
        match = re.search(
            r"^https://[^/]+/openai/deployments/[^/]+/(.+?)(\?|$)", request_url
        )
    return match[1]


def append_to_jsonl(data, filename: str) -> None:
    """Append a json payload to the end of a jsonl file."""
    json_string = json.dumps(data)
    with open(filename, "a") as f:
        f.write(json_string + "\n")
    


def num_tokens_consumed_from_request(
    request_json: dict,
    api_endpoint: str,
    token_encoding_name: str,
    json_payload: dict,
):
    """Count the number of tokens in the request. Only supports completion and embedding requests."""
    encoding = tiktoken.get_encoding(token_encoding_name)
    # if completions request, tokens = prompt + n * max_tokens
    if api_endpoint.endswith("completions"):
        max_tokens = json_payload.get("max_tokens", 3000)
        n = json_payload.get("n", 1)
        completion_tokens = n * max_tokens
        # chat completions
        if api_endpoint.startswith("chat/"):
            num_tokens = 0
            for message in json_payload["messages"]:
                num_tokens += 4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
                for key, value in message.items():
                    num_tokens += len(encoding.encode(value))
                    if key == "name":  # if there's a name, the role is omitted
                        num_tokens -= 1  # role is always required and always 1 token
            num_tokens += 2  # every reply is primed with <im_start>assistant
            return num_tokens + completion_tokens
    else:
        raise NotImplementedError(
            f'API endpoint "{api_endpoint}" not implemented in this script'
        )


def task_id_generator_function():
    """Generate integers 0, 1, 2, and so on."""
    task_id = 0
    while True:
        yield task_id
        task_id += 1

def count_jsonl_lines(file_path):
    line_count = 0
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line_count += 1
    return line_count



### Note lambda may persist /tmp folder arbitrarily. 
### May need to delete /tmp occasionally, may want to set up a flag for it.

def handler(event, context):
    
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']

    
    logger.info(f"Source bucket: {bucket}")
    logger.info(f"File: {key}") # This would be something like data/indeed_19_02_2024.json
    
    
    # Below was saving locally to change, instead can use s3.get_object
    stripped_key = key.split("/")[-1]
    try:
        local_filename = '/tmp/' + stripped_key # lambda saves to /tmp by default
        s3.download_file(bucket, key, local_filename)
        logger.info(f"{key} downloaded to {local_filename}")
    except Exception as e:
        logger.error(f"Error downloading file locally to {local_filename}:")
        logger.error(e)
        raise

    
    init_num_lines = count_jsonl_lines(local_filename)
    
    local_filename_saved = f"/tmp/{stripped_key.split('.')[0]}_saved.jsonl"
    
    asyncio.run(
        process_api_requests_from_file(
            requests_filepath=local_filename,
            save_filepath=local_filename_saved,
            request_url="https://api.openai.com/v1/chat/completions",
            api_key=str(os.getenv("OPENAI_API_KEY")),
            max_requests_per_minute=float(500),
            max_tokens_per_minute=float(59999),
            token_encoding_name="cl100k_base", # Default, should work for tiktoken and 3.5-turbo
            max_attempts=int(5),
            gpt_model=str(os.getenv("GPT_MODEL")), # testing with gpt-3.5-turbo for now
            gpt_init_prompt=str(os.getenv("GPT_PROMPT")),
            gpt_example_1=str(os.getenv("EXAMPLE_TEXT_1")),
            gpt_response_1=str(os.getenv("EXAMPLE_RESPONSE_1")),
            gpt_example_2=str(os.getenv("EXAMPLE_TEXT_2")),
            gpt_response_2=str(os.getenv("EXAMPLE_RESPONSE_2")),
            gpt_question=str(os.getenv("EXAMPLE_PROMPT")),
            gpt_temp=float(os.getenv("GPT_TEMP")),
        )
    )

    final_num_lines = count_jsonl_lines(local_filename_saved)
    
    
    # save to s3
    save_bucket_name = os.environ.get("SAVE_BUCKET_NAME")
    save_bucket_folder = os.environ.get("SAVE_FOLDER_NAME")
    full_object_key = f"{key}"  ## don't need {save_bucket_folder} as data/ in key. 
    try:
        with open(local_filename_saved, 'rb') as f:
            jsonl_data = f.read()
            
            s3.put_object(
                Bucket=save_bucket_name,
                Key=full_object_key,
                Body=jsonl_data
            )
        logger.info(f"File saved to {save_bucket_name}/{full_object_key}")
    except Exception as e:
        logger.error(f"Error saving {full_object_key} to S3 bucket {save_bucket_name}: {e}")
            
    if init_num_lines == final_num_lines:
        logger.info(f"Number of lines is consistant, async seemed to work properly")
        logger.info(f"Init # lines: {init_num_lines}, final # lines: {final_num_lines}")
    else:
        logger.warning(f"Number of lines is inconsistant, async may have been improperly implemented")
        logger.warning(f"Init # lines: {init_num_lines}, final # lines: {final_num_lines}")

