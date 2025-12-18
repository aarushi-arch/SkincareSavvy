from recommendations.scrapers.paulas_choice import PaulasChoiceScraper
from selenium.webdriver.common.by import By
import time

def debug_serums():
    scraper = PaulasChoiceScraper()
    # Go to a working page
    url = "https://www.paulaschoice.com/skin-care-products/cleansers"
    print(f"Opening {url}")
    scraper.driver.get(url)
    time.sleep(5)
    
    print("Searching for 'Serum' links...")
    # Find links with text "Serum" or "Serums"
    links = scraper.driver.find_elements(By.XPATH, "//a[contains(text(), 'Serum')]")
    for l in links:
        print(f"Text: {l.text} | Href: {l.get_attribute('href')}")
        
    scraper.driver.quit()

if __name__ == "__main__":
    debug_serums()
