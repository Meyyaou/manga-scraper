#Import all necessary libraries
import requests
from bs4 import BeautifulSoup
import pandas as pd
import urllib.parse
import random
#import matplotlib.pyplot as plt
#import seaborn as sns
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time
import logging
from dotenv import load_dotenv
import os

#Define constants
HEADERS_POOL = [
    {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36',
        'accept-language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7,ar;q=0.6'
    },
    {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'accept-language': 'en-US,en;q=0.9'
    },
    {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 '
                      '(KHTML, like Gecko) Version/17.4 Safari/605.1.15',
        'accept-language': 'en-US,en;q=0.9'
    },
]
SEARCH_URL = "https://www.amazon.com/s?k=manga&rh=n%3A4367&ref=nb_sb_noss"
MAX_RESULTS = 20
DEBUG_SAVE_HTML = False  # set True to dump each fetched page to disk for inspection

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

load_dotenv()
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_TO = os.getenv("EMAIL_TO")

if not all([EMAIL_USER, EMAIL_PASSWORD, EMAIL_TO]):
    raise ValueError(
        "Missing EMAIL_USER, EMAIL_PASSWORD or EMAIL_TO in .env"
    )

session = requests.Session()
session.headers.update(random.choice(HEADERS_POOL))


def polite_delay(a=1.5, b=3.5):
    time.sleep(random.uniform(a, b))


def fetch(url):
    session.headers.update(random.choice(HEADERS_POOL))
    try:
        resp = session.get(url, timeout=10)
        resp.raise_for_status()
        return resp
    except requests.RequestException as e:
        logging.error(f"Failed to retrieve {url}: {e}")
        return None


#to get book info from a URL
def get_book_info(url):
    resp = fetch(url)
    if resp is None:
        return None

    soup = BeautifulSoup(resp.text, 'lxml')
    page_title = soup.title.text.strip() if soup.title else "(no title)"
    logging.info(f"Fetched page: {page_title} [{resp.status_code}]")

    if DEBUG_SAVE_HTML:
        with open("debug_product.html", "w", encoding="utf-8") as f:
            f.write(resp.text)

    title_elem = soup.select_one("#productTitle")
    title = title_elem.text.strip() if title_elem else None

    author_elem = soup.select_one('span.author')
    author = author_elem.text.strip() if author_elem else None

    date_elem = soup.select_one(
        "#rpi-attribute-book_details-publication_date "
        "> div.a-section.a-spacing-none.a-text-center.rpi-attribute-value > span"
    )
    date = date_elem.text.strip() if date_elem else None

    full_price_elem = soup.select_one('span.a-price-whole')
    frac_price_elem = soup.select_one('span.a-price-fraction')
    curr_elem = soup.select_one("span.a-price-symbol")
    currency = curr_elem.text.strip() if curr_elem else '$'

    price = None
    if full_price_elem and frac_price_elem:
        whole = full_price_elem.text.strip().replace(",", "").replace(".", "")
        fraction = frac_price_elem.text.strip()
        if whole and fraction:
            try:
                price = float(f"{whole}.{fraction}")
            except ValueError:
                logging.warning(f"Could not parse price '{whole}.{fraction}' for {url}")

    order_bs_elem = soup.select_one("div.zg-badge-wrapper > a > i")
    order_bs = order_bs_elem.text.strip() if order_bs_elem else None

    cat_bs_elem = soup.select_one("div.zg-badge-wrapper > a > span > span")
    cat_bs = cat_bs_elem.text.strip() if cat_bs_elem else None

    if not title:
        logging.warning(f"No title found for {url} — possible bot-check page instead of product page")

    result = {
        'title': title,
        'author': author,
        'date': date,
        'price': price,
        'currency': currency,
        'order_bs': order_bs,
        'cat_bs': cat_bs
    }
    logging.info(result)
    return result


#to list search results
def search_res_listing(url_search, books_data):
    resp = fetch(url_search)
    if resp is None:
        return books_data

    if DEBUG_SAVE_HTML:
        with open("debug_search.html", "w", encoding="utf-8") as f:
            f.write(resp.text)

    search_soup = BeautifulSoup(resp.text, 'lxml')
    page_title = search_soup.title.text.strip() if search_soup.title else "(no title)"
    logging.info(f"Search page: {page_title} [{resp.status_code}]")

    # Scope link extraction to the actual result cards, not every /dp/ link on the page
    # (nav bar, sponsored carousels, "also bought" widgets, etc. all contain /dp/ links too).
    products = search_soup.select('div[data-component-type="s-search-result"]')
    logging.info(f"Found {len(products)} product cards on this page")

    url_elem_list = []
    for product in products:
        link = product.select_one('a[href*="/dp/"]')
        if link and link.get('href'):
            href = link['href'].split("?")[0]
            if href not in url_elem_list:
                url_elem_list.append(href)

    logging.info(f"Deduplicated product URLs: {url_elem_list}")

    for url_elem in url_elem_list:
        if len(books_data) >= MAX_RESULTS:
            logging.info("Counter reached MAX_RESULTS")
            return books_data

        url = urllib.parse.urljoin(url_search, url_elem)
        logging.info(f"Processing URL: {url}")
        polite_delay()
        book_info = get_book_info(url)
        if book_info:
            books_data.append(book_info)

    #Pagination handling
    next_book_el = search_soup.select_one('a.s-pagination-next')
    if next_book_el and next_book_el.get('href') and len(books_data) < MAX_RESULTS:
        next_book_url = urllib.parse.urljoin(url_search, next_book_el['href'])
        logging.info(f"Next page URL: {next_book_url}")
        polite_delay(2, 4)
        books_data = search_res_listing(next_book_url, books_data)

    return books_data


#to preprocess the data
def preprocess_data(dataframe):
    dataframe['date'] = pd.to_datetime(dataframe['date'], errors='coerce')

    for i, auth in enumerate(dataframe['author']):
        if auth:
            parts = auth.split()
            first = parts[0] if parts else ""
            second = parts[1] if len(parts) > 1 and 'Author' not in parts[1] else ""
            dataframe.at[i, "author"] = f"{first} {second}".strip().split("\n")[0]

    dataframe['cat_bs'] = dataframe['cat_bs'].fillna("No bs")
    # Store as a plain string (not a list) so it round-trips correctly through CSV.
    dataframe['cat_bs'] = dataframe['cat_bs'].apply(
        lambda x: " ".join(w for w in str(x).split() if w not in ['in', '&']) if x != 'No bs' else "No bs"
    )

    dataframe['order_bs'] = dataframe['order_bs'].fillna("No bs")
    return dataframe


#to visualize the data (basic plotting)
"""def visualize_data(dataframe):
    plt.hist(dataframe['date'], bins=20)
    plt.figure()
    plt.plot(dataframe['price'], c='green', marker='o', linestyle='-')
    plt.xlabel('Index')
    plt.ylabel('Price ($)')
    plt.tight_layout()
    plt.show()
"""


#Function to send email alerts
def email_alert(subject, body):
    msg = MIMEMultipart()
    msg.attach(MIMEText(body, 'plain'))
    msg['Subject'] = subject
    msg['To'] = EMAIL_TO
    msg['From'] = EMAIL_USER
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.send_message(msg)
        logging.info("Email sent successfully")
    except Exception as e:
        logging.error(f"Failed to send email: {e}")


#Function to analyze variations
def variation_analysis(old_data_path, new_data_path):
    old_data = pd.read_csv(old_data_path)
    new_data = pd.read_csv(new_data_path)

    for ind, row in new_data.iterrows():
        old_row = old_data[old_data['title'] == row['title']]

        if not old_row.empty:
            old_row = old_row.iloc[0]
            if pd.notna(row["price"]) and pd.notna(old_row['price']):
                if abs(row['price'] - old_row['price']) > 0.01:
                    email_alert(
                        'Price Changing',
                        f"the price of {row['title']} has changed from {old_row['price']} to {row['price']}"
                    )

            if row['order_bs'] != old_row['order_bs']:
                email_alert(
                    'Order of Best Seller Changing',
                    f"{row['title']} that had {old_row['order_bs']} as an order of best selling, "
                    f"in {old_row['cat_bs']} category(ies) before, has now an order of "
                    f"{row['order_bs']} in {row['cat_bs']} category(ies)"
                )
        else:
            email_alert(
                'New manga added',
                f"A new manga has appeared in your best sellers search results: {row['title']} "
                f"by {row['author']} published in {row['date']} is at position {row['order_bs']} "
                f"in category {row['cat_bs']}."
            )

    for ind, row in old_data.iterrows():
        if row['title'] not in new_data['title'].values:
            email_alert(
                'Manga disappeared!',
                f"the manga {row['title']} by {row['author']}, published in {row['date']} is no longer a best-seller"
            )

    new_data.to_csv('m_amazon_2.csv', index=False)


#Main function to execute the script
def main():
    books_data = search_res_listing(SEARCH_URL, [])
    dataframe = pd.DataFrame(books_data)
    dataframe.to_csv("m_amazon_1.csv", index=False, sep=',')

    #dataframe = preprocess_data(dataframe)
    #visualize_data(dataframe)

    #Variation analysis example
    old_data_path = 'mangas_amazon_test1.csv'
    new_data_path = 'm_amazon_1.csv'
    #variation_analysis(old_data_path, new_data_path)


if __name__ == "__main__":
    main()
