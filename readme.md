# Anandabazar News Scraper

This Python script scrapes news articles from the Anandabazar website, focusing on articles related to specific disaster-related keywords. It processes articles from yesterday, extracts relevant information, and outputs statistics on the number of articles found for each keyword.

## Features

- **Web Scraping**: Utilizes Selenium to load web pages and BeautifulSoup to parse HTML content.
- **Date Conversion**: Converts Bangla date strings to Gregorian dates to filter articles from yesterday.
- **Keyword Filtering**: Filters articles based on predefined keywords found in the article links.
- **Statistics**: Outputs the count of articles and their URLs for each keyword.

## Setup

### Prerequisites

- **Python 3.x**
- **Selenium**: Install using `pip install selenium`
- **BeautifulSoup4**: Install using `pip install beautifulsoup4`
- **ChromeDriver**: Ensure ChromeDriver is installed and available in your system's PATH. Download the correct version for your Chrome browser from [ChromeDriver Downloads](https://sites.google.com/a/chromium.org/chromedriver/).

### Installation

1. **Clone the Repository**: 
   ```bash
   git clone git@github.com:Shaikh-Rehan-Shakil/anaanda-baazar-scraper.git
   cd anaanda-baazar-scraper
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. **Run the Script**:
   ```bash
   python script.py
   ```

2. **Output**: The script will print the number of articles found for each keyword and their URLs.

## Customization

- **States**: Modify the `states` list in the script to scrape different regions.
- **Keywords**: Update the `KEYWORDS` list to filter articles based on different terms.


