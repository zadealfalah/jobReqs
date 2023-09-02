from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
import time
import json
import re
from bs4 import BeautifulSoup as bs
from urllib.parse import urlencode


# def main():
#     options = webdriver.FirefoxOptions()
#     driver = webdriver.Firefox(options=options)

    
    
    
#     jobs = scrape_jobs()



def scrape_jobs(query:str, location:str):
    options = webdriver.FirefoxOptions()
    driver = webdriver.Firefox(options=options)
    
    def make_page_url(offset):
        params = {"q": query, "l": location, "start":offset}
        return "https://www.indeed.com/jobs?" + urlencode(params)
    print(f"Scraping first page of search: {query=}, {location=}")
    
    print(f"First URL: {make_page_url(0)}")
    driver.get(make_page_url(0))
    soup = bs(driver.page_source)
    
    results = soup.find(id='jobsearch-Main')
    job_elements = results.find_all("div", class_="slider_item")
    d = {}
    for job_element in job_elements[:1]:
        link_element_id = job_element.find_all("a")[0]["id"]

        d[link_element_id] = {}
        d[link_element_id]["title"] = job_element.find("h2", class_="jobTitle").text.strip()
        d[link_element_id]['company'] = job_element.find("span", class_="companyName").text.strip()
        d[link_element_id]['posted'] = job_element.find("span", class_="date").next_element.next_element.next_element
        try:
            d[link_element_id]['location'] = job_element.find("div", class_="companyLocation").text.strip()
        except AttributeError: 
            d[link_element_id]['location'] = "Not Listed"
        try:
            d[link_element_id]['salary'] = job_element.find("div", class_="metadata").text.strip()
        except AttributeError:
            d[link_element_id]['salary'] = "Not Listed"
        # date_element = job_element.find("div", class_="visually-hidden")  # not useful as-is.  figure out if this is possible to find at all

        WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.XPATH, f'//*[@id="{link_element_id}"]'))).click()


        time.sleep(5)
        
        temp_results = soup.find("div", id='jobDescriptionText')
        print(temp_results)
        print(d[link_element_id]["title"], d[link_element_id]["company"])
        # print(d[link_element_id]['title'], d[link_element_id]['company'])
        d[link_element_id]['desc'] = temp_results.text.strip()
    
    return d

scrape_jobs(query='python', location='remote')

# options = webdriver.FirefoxOptions()
# driver = webdriver.Firefox(options=options)
# driver.get("https://www.indeed.com/jobs?q=data+science&l=remote")

# soup = bs(driver.page_source)

# results = soup.find(id="jobsearch-Main")
# job_elements = results.find_all("div", class_="slider_item")

# basePath = "https://www.indeed.com"
# d = {}
# # Currently using link_element_id as unique ID.  I am fairly sure it's unique - at least it has been from what I've seen so far.
# for job_element in job_elements[:1]:
#     link_element_id = job_element.find_all("a")[0]["id"]

#     d[link_element_id] = {}
#     d[link_element_id]["title"] = job_element.find("h2", class_="jobTitle").text.strip()
#     d[link_element_id]['company'] = job_element.find("span", class_="companyName").text.strip()
#     d[link_element_id]['posted'] = job_element.find("span", class_="date").next_element.next_element.next_element
#     try:
#         d[link_element_id]['location'] = job_element.find("div", class_="companyLocation").text.strip()
#     except AttributeError: 
#         d[link_element_id]['location'] = "Not Listed"
#     try:
#         d[link_element_id]['salary'] = job_element.find("div", class_="metadata").text.strip()
#     except AttributeError:
#         d[link_element_id]['salary'] = "Not Listed"
#     # date_element = job_element.find("div", class_="visually-hidden")  # not useful as-is.  figure out if this is possible to find at all

#     WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.XPATH, f'//*[@id="{link_element_id}"]'))).click()

#     time.sleep(2)
#     temp_results = results.find("div", id='jobDescriptionText')
#     # print(d[link_element_id]['title'], d[link_element_id]['company'])
#     d[link_element_id]['desc'] = temp_results.text.strip()