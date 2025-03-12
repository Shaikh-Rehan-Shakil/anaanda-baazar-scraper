from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import unicodedata
import json

# List of states to scrape
states = [
    "bardhaman",
    "north-bengal",
    "midnapore",
    "howrah-hooghly",
    "purulia-birbhum-bankura",
    "24-parganas",
    "nadia-murshidabad",
]

# Disaster keywords dictionary
keywords = {
    "flood": ["flood", "inundation", "waterlogging", "deluge"],
    "fire": ["fire", "blaze", "inferno", "burn", "flames"],
    "earthquake": ["earthquake", "tremor", "seismic"],
    "cyclone": ["cyclone", "storm", "hurricane", "typhoon"],
}

# Initialize statistics dictionary based on keywords dictionary
stats = {disaster: {"count": 0, "articles": []} for disaster in keywords}


def scrape_page(url):
    """
    Scrape a single page for article links and process relevant ones.
    """
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.page_load_strategy = "eager"
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    )

    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(30)

    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.imgntextbox"))
        )
        soup = BeautifulSoup(driver.page_source, "html.parser")
        containers = soup.find_all("div", class_="imgntextbox")
        for container in containers:
            link_element = container.find("a")
            if not link_element:
                continue
            article_link = link_element.get("href")
            if article_link and not article_link.startswith("http"):
                article_link = "https://www.anandabazar.com" + article_link
            link_text = article_link.lower()
            matched_disasters = [
                d for d in keywords if any(term in link_text for term in keywords[d])
            ]
            for disaster in matched_disasters:
                stats[disaster]["count"] += 1
                stats[disaster]["articles"].append(article_link)
    finally:
        driver.quit()


def scrape_section(section, pages=5):
    """
    Scrape a specific news section with multiple pages.
    """
    with ThreadPoolExecutor(max_workers=5) as executor:
        urls = [
            f"https://www.anandabazar.com/west-bengal/{section}/page-{i}"
            for i in range(1, pages + 1)
        ]
        executor.map(scrape_page, urls)


def main():
    """
    Main function to scrape data for West Bengal news and all state sections.
    """
    scrape_section("page", pages=5)
    for state in states:
        scrape_section(state, pages=5)
    json_output = json.dumps(stats, ensure_ascii=False, indent=4)
    print("\n📊 JSON Output:")
    print(json_output)


if __name__ == "__main__":
    main()
