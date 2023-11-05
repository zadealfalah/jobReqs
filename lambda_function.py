try:
    import json
    from selenium import webdriver
    from selenium.webdriver import Chrome
    from selenium.webdriver.chrome.options import Options
    import os
    import shutil
    import uuid
    import boto3
    from datetime import datetime
    import datetime
    from selenium_stealth import stealth

    print("All Modules are ok ...")

except Exception as e:

    print(f"Error in Imports: {e} ")




def lambda_handler(event, context):
    
    options = Options()
    options.binary_location = '/opt/headless-chromium'
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--start-maximized')
    options.add_argument('--start-fullscreen')
    options.add_argument('--single-process')
    options.add_argument('--disable-dev-shm-usage')
    driver = Chrome('/opt/chromedriver', options=options)
    driver.get("https://github.com")
    print(driver.title)
    return True
