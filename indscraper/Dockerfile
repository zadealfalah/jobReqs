# Use the official Python image from Docker Hub
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy full project dir to container
COPY . .

# Install spacy and download en_core_web_sm
# RUN pip install spacy && \
#     python -m spacy download en_core_web_sm

# Install other dependencies from requirements.txt
COPY scraper_requirements.txt ./
RUN pip install --no-cache-dir -r scraper_requirements.txt

# Set the working directory to the Scrapy project directory
WORKDIR /app/indscraper

# Set the command to run the Scrapy crawl
CMD ["scrapy", "crawl", "indeedjobs"]