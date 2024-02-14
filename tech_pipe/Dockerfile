# Lambda implementation here.
FROM public.ecr.aws/lambda/python:3.10

# Set the working directory in the container
WORKDIR /app

# Copy full project dir to container
COPY . /app


# Install other dependencies from requirements.txt
COPY tech_requirements.txt ./
RUN pip install --no-cache-dir -r tech_requirements.txt
# Must be done after spacy install
RUN python -m spacy download en_core_web_sm


# Set the command to run the Scrapy crawl
CMD ["python", "main.py"]




# # Copy full project dir to container
# COPY . .

# # Install spacy and download en_core_web_sm
# # RUN pip install spacy && \
# #     python -m spacy download en_core_web_sm

# # Install other dependencies from requirements.txt
# COPY requirements.txt ./
# RUN pip install --no-cache-dir -r requirements.txt

# # Set the working directory to the Scrapy project directory
# WORKDIR /app/indscraper

# # Set the command to run the Scrapy crawl
# CMD ["scrapy", "crawl", "indeedjobs"]