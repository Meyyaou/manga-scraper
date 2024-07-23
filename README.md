# Amazon Manga Scraper

This project is a web scraping script designed to extract manga book information from Amazon search results using Python and BeautifulSoup. The script sends a request to the Amazon search page for manga, parses the HTML content, and retrieves details of the books listed. 

## Features

- Scrapes Amazon search results for manga books.
- Extracts book information such as URL and title.
- Handles pagination to fetch results from multiple pages.
- Sends email alerts if any data changes.
- Includes detailed debugging information for troubleshooting.


## Requirements

- Python 3.x
- `requests` library
- `beautifulsoup4` library
- `lxml` library
- `smtplib` library (for sending emails)

1. Configure your email settings in the `send_email_alert` function:

    ```python
    def send_email_alert(changes):
        sender = "sender@gmail.com"
        receiver = "rec@gmail.com"
        password = "your-email-password"/"your-app-password"
        subject = "Amazon Manga Scraper Alert"
        body = f"Changes detected:\n\n{changes}"

        message = f"""From: {sender}
        To: {receiver}
        Subject: {subject}

        {body}
        """

        try:
            smtp_obj = smtplib.SMTP('smtp.example.com', 587)
            smtp_obj.starttls()
            smtp_obj.login(sender, password)
            smtp_obj.sendmail(sender, receiver, message)
            smtp_obj.quit()
            print("Email sent successfully")
        except Exception as e:
            print(f"Error: unable to send email: {e}")
    ```

3. Run the script:

    ```bash
    python scraper.py
    ```

4. The script will print the extracted book information to the console and send an email alert if any data changes are detected.

## Debugging

The script includes several print statements to help with debugging:

- The status code of the HTTP response.
- The list of links found on the search results page.
- The list of URLs extracted from the links.
- The URL being processed for each book.
- The next page URL for pagination.

## Example Output

## Perspectives
- **Fixing URL Issues:** The current script is facing issues with extracting URLs correctly. This will be addressed in the next update.
- **Scheduled Execution:** A feature will be added to enable the script to run automatically every 5 days, ensuring the data is always up-to-date.
