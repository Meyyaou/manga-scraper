# import all necessary libraries
import requests
from bs4 import BeautifulSoup
import pandas as pd
import lxml
import urllib.parse
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time

HEADER = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36',
    'accept-language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7,ar;q=0.6'
}
SEARCH_URL = "https://www.amazon.com/s?k=manga&rh=n%3A4367&ref=nb_sb_noss"
MAX_RESULTS = 20

#page=requests.get(url,headers=HEADER)
#soup=BeautifulSoup(page.text, 'lxml')
#print('status is :', page.status_code)

#to get book info from a URL
def get_book_info(url):
    page = requests.get(url, headers=HEADER)
    soup = BeautifulSoup(page.text, 'lxml')
    #for debug
    #print('the page status ', page.status_code)

    title_elem = soup.select_one("#productTitle")
    title = title_elem.text.strip() if title_elem else None
    #print(title)

    author_elem = soup.select_one('span.author')
    author = author_elem.text.strip() if author_elem else None
    #print(author)

    date_elem = soup.select_one("#rpi-attribute-book_details-publication_date > div.a-section.a-spacing-none.a-text-center.rpi-attribute-value > span")
    date = date_elem.text.strip() if date_elem else None
    #print(date)

    full_price_elem = soup.select_one('span.a-price-whole')
    frac_price_elem = soup.select_one('span.a-price-fraction')
    curr_elem = soup.select_one("span.a-price-symbol")
    price = (full_price_elem.text + frac_price_elem.text + curr_elem.text).strip() if full_price_elem and frac_price_elem and curr_elem else None
    #print(price)

    order_bs_elem = soup.select_one("div.zg-badge-wrapper > a > i")
    order_bs = order_bs_elem.text.strip() if order_bs_elem else None

    cat_bs_elem = soup.select_one("div.zg-badge-wrapper > a > span > span")
    cat_bs = cat_bs_elem.text.strip() if cat_bs_elem else None
    #print(order_bs, cat_bs)
  
    #for debug
    '''print("the manga: ",{
        'title': title,
        'author': author,
        'date': date,
        'price': price,
        'order_bs': order_bs,
        'cat_bs': cat_bs
    })'''
  
    return {
        'title': title,
        'author': author,
        'date': date,
        'price': price,
        'order_bs': order_bs,
        'cat_bs': cat_bs
    }

# to list search results
def search_res_listing(url_search, books_data):
    global counter
    response = requests.get(url_search, headers=HEADER)
  
    #for debug
    print('The result status:', response.status_code)

    if response.status_code != 200:
        print("Failed to retrieve the page")
        return books_data

    search_soup = BeautifulSoup(response.text, 'lxml')
    links = search_soup.find_all("a", attrs={'class':"a-link-normal s-underline-text s-underline-link-text s-link-style a-text-normal"})
    
    #for debug
    print('list of links:', links)
    
    url_elem_list = []
    for link in links:
        href = link.get('href')
        if href and href.startswith('/'):
            url_elem_list.append(href)
    #for debug
    print("list of urls:", url_elem_list)
    
    for url_elem in url_elem_list:
        if counter >= MAX_RESULTS:
            print("Counter reached MAX_RESULTS")
            return books_data
        
        url = urllib.parse.urljoin(url_search, url_elem)
        print("Processing URL:", url)  # Print the URL being processed
        book_info = get_book_info(url)
        books_data.append(book_info)
        counter += 1

    # pagination handling
    next_book_el = search_soup.select_one('a.s-pagination-next')
    if next_book_el and counter < MAX_RESULTS:
        next_book_url = next_book_el.attrs.get('href')
        next_book_url = urllib.parse.urljoin(url_search, next_book_url)
        #for debug
        print("Next page URL:", next_book_url)
        time.sleep(2)  # Delay between requests
        books_data = search_res_listing(next_book_url, books_data)

    return books_data

#to preprocess the data
def preprocess_data(dataframe):
    dataframe['date'] = pd.to_datetime(dataframe['date'], errors='coerce')

    for i, auth in enumerate(dataframe['author']):
        if auth:
            auth = auth.split(" ")
            auth_name = auth[0] + ' ' + (auth[1] if len(auth) > 1 and 'Author' not in auth[1] else "")
            dataframe.at[i, "author"] = auth_name.split("\n")[0]

    dataframe['cat_bs'] = dataframe['cat_bs'].fillna("No bs")
    dataframe['cat_bs'] = dataframe['cat_bs'].apply(lambda x: [word for word in str(x).split() if word not in ['in', '&']] if x != 'No bs' else ["No bs"])

    dataframe['order_bs'] = dataframe['order_bs'].fillna("No bs")
    return dataframe

# to visualize the data (basic plotting)
"""def visualize_data(dataframe):
    plt.hist(dataframe['date'], bins=20)
    plt.figure()
    plt.plot(dataframe['price'], c='green', marker='o', linestyle='-')
    plt.xlabel('Index')
    plt.ylabel('Price ($)')
    plt.tight_layout()
    plt.show()
"""
# to send email alerts
def email_alert(subject, body, to):
    msg = MIMEMultipart()
    msg.attach(MIMEText(body, 'plain'))
    msg['subject'] = subject
    msg['to'] = to
    user = 'sender@gmail.com'
    msg['from'] = user
    pwd = 'x'

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(user, pwd)
    server.send_message(msg)
    server.quit()

# Function to analyze variations
def variation_analysis(old_data_path, new_data_path):
    old_data = pd.read_csv(old_data_path)
    new_data = pd.read_csv(new_data_path)

    for ind, row in new_data.iterrows():
        old_row = old_data[old_data['title'] == row['title']]

        if not old_row.empty:
            #print("hey old_row is not empty")
            old_row = old_row.iloc[0]

            if row['price'] != old_row['price']:
                #rint('prices are no longer same\n')
                email_alert('Price Changing', f"the price of {row['title']} has changed from {old_row['price']} to {row['price']}", 'rec@gmail.com')

            if row['order_bs'] != old_row['order_bs']:
                #print('order of best selling are no longer same')
                email_alert('Order of Best Seller Changing', f"{row['title']} that had {old_row['order_bs']} as an order of best selling, in {old_row['cat_bs']} category(ies) before, has now an order of {row['order_bs']} in {row['cat_bs']} category(ies)", 'rec@gmail.com')
        else:
            #print('new manga added !')
            email_alert('New manga added', f"A new manga has appeared in your best sellers search results: {row['title']} by {row['author']} published in {row['date']} is at position {row['order_bs']} in category {row['cat_bs']}.", 'rec@gmail.com')

    for ind, row in old_data.iterrows():
        if row['title'] not in new_data['title'].values:
            #print('a manga has disappeared')
            email_alert('Manga disappeared!', f"the manga {row['title']} by {row['author']}, published in {row['date']} is no longer a best-seller", 'rec@gmail.com')

    new_data.to_csv('m_amazon_2.csv', index=False)

# Main function to execute the script
def main():
    books_data = search_res_listing(SEARCH_URL, [])
    dataframe = pd.DataFrame(books_data)
    dataframe.to_csv("m_amazon_1.csv", index=False, sep=',')
    
    #dataframe = preprocess_data(dataframe)
    #visualize_data(df)

    # Variation analysis example
    old_data_path = 'mangas_amazon_test1.csv'
    new_data_path = 'm_amazon_1.csv'
    #variation_analysis(old_data_path, new_data_path)

if __name__ == "__main__":
    counter = 0
    main()
