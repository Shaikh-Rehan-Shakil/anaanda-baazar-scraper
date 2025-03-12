import re
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
import time

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

# Store processed URLs to avoid duplicates
processed_urls = set()


def normalize_text(text):
    """
    Normalize the text to remove diacritics and other combining characters.
    """
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(c for c in normalized if not unicodedata.combining(c))


# Original mapping of Bangla months to English months
BANGLA_TO_ENGLISH_MONTHS_ORIGINAL = {
    "জানুয়ারি": "January",
    "ফেব্রুয়ারি": "February",
    "মার্চ": "March",
    "এপ্রিল": "April",
    "মে": "May",
    "জুন": "June",
    "জুলাই": "July",
    "আগস্ট": "August",
    "সেপ্টেম্বর": "September",
    "অক্টোবর": "October",
    "নভেম্বর": "November",
    "ডিসেম্বর": "December",
}

# Create a normalized dictionary mapping for Bangla months
BANGLA_TO_ENGLISH_MONTHS = {
    normalize_text(key): value
    for key, value in BANGLA_TO_ENGLISH_MONTHS_ORIGINAL.items()
}


def extract_bangla_date(date_text):
    """
    Extract the Bangla date from the text.
    Example: "শেষ আপডেট: ১০ মার্চ ২০২৫ ০৯:০৫" -> "১০ মার্চ ২০২৫"
    """
    try:
        parts = date_text.split()
        if len(parts) >= 4:
            return " ".join(parts[2:5])
        return None
    except Exception as e:
        print(f"⚠️ Error extracting Bangla date: {e}")
        return None


def convert_bangla_to_english_numerals(bangla_number):
    """
    Convert Bangla numerals to English numerals.
    Example: "১০" -> "10"
    """
    bangla_to_english_digits = {
        "০": "0",
        "১": "1",
        "২": "2",
        "৩": "3",
        "৪": "4",
        "৫": "5",
        "৬": "6",
        "৭": "7",
        "৮": "8",
        "৯": "9",
    }
    return "".join([bangla_to_english_digits.get(char, char) for char in bangla_number])


def convert_bangla_to_gregorian(bangla_date):
    """
    Convert a Bangla date string (e.g., "১০ মার্চ ২০২৫") to a Gregorian date object.
    """
    try:
        day, month, year = bangla_date.split()
        normalized_month = normalize_text(month)
        english_month = BANGLA_TO_ENGLISH_MONTHS.get(normalized_month)
        if not english_month:
            raise ValueError(f"Unrecognized Bangla month: {month}")
        day = convert_bangla_to_english_numerals(day)
        year = convert_bangla_to_english_numerals(year)
        gregorian_date_str = f"{day} {english_month} {year}"
        return datetime.strptime(gregorian_date_str, "%d %B %Y")
    except Exception as e:
        print(f"⚠️ Error converting Bangla date to Gregorian: {e}")
        return None


def is_yesterday(bangla_date):
    """
    Check if the Bangla date corresponds to yesterday's date.
    """
    try:
        gregorian_date = convert_bangla_to_gregorian(bangla_date)
        if not gregorian_date:
            return False
        yesterday = datetime.now() - timedelta(days=1)
        return gregorian_date.strftime("%Y-%m-%d") == yesterday.strftime("%Y-%m-%d")
    except Exception as e:
        print(f"⚠️ Error comparing dates: {e}")
        return False


def contains_keywords(text, keywords_dict):
    """
    Check if the text contains any keywords from each disaster category using regex.
    Returns a list of disaster types that match.
    """
    text = text.lower()
    matched_disasters = []
    for disaster, terms in keywords_dict.items():
        # Create regex pattern with word boundaries for each term
        pattern = (
            r"\b(?:" + "|".join(re.escape(term.lower()) for term in terms) + r")\b"
        )
        if re.search(pattern, text):
            matched_disasters.append(disaster)
    return matched_disasters


# Create a driver pool for reusing WebDriver instances
class WebDriverPool:
    def __init__(self, max_drivers=3):
        self.max_drivers = max_drivers
        self.drivers = []
        self.in_use = {}

    def get_driver(self):
        """Get an available driver or create a new one if needed and available"""
        # First try to find an unused driver
        for driver in self.drivers:
            if not self.in_use.get(driver, False):
                self.in_use[driver] = True
                return driver

        # If no unused drivers and we haven't reached max, create a new one
        if len(self.drivers) < self.max_drivers:
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
            driver.set_page_load_timeout(20)
            self.drivers.append(driver)
            self.in_use[driver] = True
            return driver

        # If all drivers are in use, wait until one is available
        while True:
            for driver in self.drivers:
                if not self.in_use.get(driver, False):
                    self.in_use[driver] = True
                    return driver
            time.sleep(0.5)

    def release_driver(self, driver):
        """Mark a driver as no longer in use"""
        if driver in self.drivers:
            self.in_use[driver] = False

    def quit_all(self):
        """Quit all drivers"""
        for driver in self.drivers:
            try:
                driver.quit()
            except:
                pass
        self.drivers = []
        self.in_use = {}


# Initialize the WebDriver pool
driver_pool = WebDriverPool(max_drivers=3)


def scrape_page(url):
    """
    Scrape a single page for article links and process relevant ones.
    Uses a driver from the pool for better performance.
    """
    if url in processed_urls:
        print(f"Skipping already processed URL: {url}")
        return

    processed_urls.add(url)
    print(f"Scraping page: {url}")

    driver = None
    try:
        # Get a driver from the pool
        driver = driver_pool.get_driver()

        # Implement retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                driver.get(url)
                # Wait for the content to load with a reasonable timeout
                WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located(
                        (By.CSS_SELECTOR, "div.imgntextbox")
                    )
                )
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2**attempt  # Exponential backoff
                    print(f"Attempt {attempt+1} failed, retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
                else:
                    raise

        soup = BeautifulSoup(driver.page_source, "html.parser")
        page_title = soup.title.string if soup.title else "No title"
        print(f"Page title: {page_title}")

        containers = soup.find_all("div", class_="imgntextbox")
        print(f"Found {len(containers)} article containers on {url}")

        for container in containers:
            try:
                link_element = container.find("a")
                if not link_element:
                    continue

                article_link = link_element.get("href")
                article_title = link_element.get_text(strip=True)

                if not article_link:
                    continue

                if not article_link.startswith("http"):
                    article_link = "https://www.anandabazar.com" + article_link

                # Check both the URL and the title for keywords
                matched_disasters = contains_keywords(
                    article_link.lower(), keywords
                ) or contains_keywords(article_title.lower(), keywords)

                if matched_disasters:
                    print(
                        f"✓ Matched disasters {matched_disasters} for: {article_title}"
                    )
                    for disaster in matched_disasters:
                        if article_link not in stats[disaster]["articles"]:
                            stats[disaster]["count"] += 1
                            stats[disaster]["articles"].append(article_link)
            except Exception as e:
                print(f"Error processing article container: {e}")
    except Exception as e:
        print(f"Error scraping page {url}: {e}")
    finally:
        if driver:
            driver_pool.release_driver(driver)
        print(f"Finished scraping page: {url}")


def generate_urls(section, pages):
    """
    Generate the correct URLs based on the section.
    """
    # For the main West Bengal section, use a different URL format
    if section == "main":
        return [
            f"https://www.anandabazar.com/west-bengal/page-{i}"
            for i in range(1, pages + 1)
        ]
    else:
        # For state-specific sections, use the original format
        return [
            f"https://www.anandabazar.com/west-bengal/{section}/page-{i}"
            for i in range(1, pages + 1)
        ]


def scrape_section(section, pages=3):
    """
    Scrape a specific news section with multiple pages.
    """
    print(f"\n=== Scraping section: {section} for {pages} pages ===")

    # Generate appropriate URLs based on the section
    urls = generate_urls(section, pages)

    for url in urls:
        print(f"Queued URL: {url}")

    with ThreadPoolExecutor(max_workers=3) as executor:
        executor.map(scrape_page, urls)


def main():
    """
    Main function to scrape data for West Bengal news and all state sections.
    """
    print("Starting optimized scraping process...\n")
    start_time = time.time()

    try:
        # Scrape the main West Bengal section
        scrape_section("main", pages=3)

        # Scrape state-specific sections
        for state in states:
            scrape_section(state, pages=2)

        # Print summary and stats
        total_articles = sum(data["count"] for data in stats.values())
        unique_articles = len(
            set().union(*(data["articles"] for data in stats.values()))
        )

        print("\n===== SCRAPING RESULTS =====")
        print(f"Total disaster-related articles: {total_articles}")
        print(f"Unique disaster-related articles: {unique_articles}")

        for disaster, data in stats.items():
            print(f"{disaster.capitalize()}: {data['count']} articles")

        print(f"\nTime elapsed: {time.time() - start_time:.2f} seconds")

        # Export to JSON file
        with open("disaster_news_stats.json", "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=4)
        print("\nResults saved to disaster_news_stats.json")

    finally:
        # Make sure to quit all WebDriver instances
        driver_pool.quit_all()


if __name__ == "__main__":
    main()
