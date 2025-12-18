from selenium import webdriver 
from selenium.webdriver.common.by import By 
from selenium.webdriver.chrome.service import Service 
from selenium.webdriver.chrome.options import Options 
from webdriver_manager.chrome import ChromeDriverManager
import time 

# ---------- CONFIG ---------- 
BASE_URL = "https://www.paulaschoice.com/skin-care-products/cleansers" 
# ---------------------------- 

options = Options() 
options.add_argument("--start-maximized") 
options.add_argument("--headless=new") # Must use headless in this env usually
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")

service = Service(ChromeDriverManager().install()) 
driver = webdriver.Chrome(service=service, options=options) 

try: 
    print("Opening page...") 
    driver.get(BASE_URL) 

    time.sleep(5)  # wait for JS to load 
    
    # Print page title
    print(f"Page Title: {driver.title}")

    # find product links 
    products = driver.find_elements(By.CSS_SELECTOR, "a[href*='/products/']") 

    print(f"Found {len(products)} products\n") 

    seen = set() 
    for p in products: 
        link = p.get_attribute("href") 
        if link and link not in seen: 
            seen.add(link) 
            print(link) 
            
    if len(products) == 0:
        print("Searching for any product-like links...")
        all_links = driver.find_elements(By.TAG_NAME, "a")
        for a in all_links:
            href = a.get_attribute('href')
            text = a.get_attribute('textContent').strip()
            if href and ("cleanser" in href.lower() or "cleanser" in text.lower()):
                print(f"Possible match: {text} -> {href}")

finally: 
    driver.quit() 
