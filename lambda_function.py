from selenium import webdriver

def lambda_handler(event, context):
    driver = webdriver.Chrome()
    driver.get('http://www.google.com')
    print(driver.title)
    driver.quit()
