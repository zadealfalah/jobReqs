# Lambda implementation here.
FROM public.ecr.aws/lambda/python:3.10


# Copy full project dir to container
COPY . ${LAMBDA_TASK_ROOT}

RUN pip install -r gpt_requirements.txt

CMD ["main.handler"]