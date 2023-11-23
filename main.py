# docker build -t jobscraping . 
# docker run jobscraping

import time

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from urllib.parse import urlencode
from collections import deque, defaultdict


chrome_options = Options()
chrome_options.add_argument("--no-sandbox") 
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-dev-shm-usage")  # use /tmp, write to disk for more memory

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

url = 'https://www.indeed.com/m/basecamp/viewjob?viewtype=embdedded&jk=05d5ae95263506e2'

try:
    driver.get(url)
    print(f"Got {url}!")
except Exception as e:
    print(f"Error getting URL: {e}")

soup = BeautifulSoup(driver.page_source, features='lxml')

for part in soup.select('h1[class*="JobInfoHeader"]'):
    print(part.get_text())

driver.quit()

