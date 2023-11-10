try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium_stealth import stealth

    print("All Modules are ok ...")

except Exception as e:
    print(f"Error in Imports: {e}")


# from selenium import webdriver


def lambda_handler(event=None, context=None):
    options = Options()
    options.add_argument("start-maximized")

    # Chrome is controlled by automated test software
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    s = Service('/usr/local/bin/chromedriver')
    driver = webdriver.Chrome(service=s, options=options)
    try:
        stealth(driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
        )

        print(f"Driver stealthed!")
    except Exception as e:
        print(f"Error stealthing: {e}")
    # Test the stealth itself
    driver.get("https://bot.sannysoft.com/")
    driver.save_screenshot(f"test_stealth_d.png")
    
    path = "https://example.com"
    driver.get(path)

    return path.title

if __name__ == "__main__":
    print("Yep")
    title = lambda_handler()
    print(title)