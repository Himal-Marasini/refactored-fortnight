import csv
import math
import requests
import os
import time
from bs4 import BeautifulSoup
from urllib.parse import urlencode, quote_plus
from modules.scrapper import Scrapper  # Ensure this import works based on your project structure
from modules.info_reader import InfoReader  # Ensure this import works based on your project structure

class YellowPageScraper:
    def __init__(self, search_terms, file_path='business_data.csv'):
        self.search_terms = search_terms
        self.file_path = file_path
        self.base_url = 'https://www.yellowpages.com'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.140 Safari/537.36'}
        self.total_businesses_collected = 0

    def extract_business_listing(self, card):
        rank = card.select_one('.info-primary h2')
        rank = rank.text.strip().split('. ')[0] if rank else ''

        business_name = card.select_one('.business-name span')
        business_name = business_name.text.strip() if business_name else ''

        phone_number = card.select_one('.phones')
        phone_number = phone_number.text.strip() if phone_number else ''

        business_page = card.select_one('.business-name')
        business_page = self.base_url + business_page['href'] if business_page else ''

        website = card.select_one(".track-visit-website")
        website = website['href'] if website else ''

        category = card.select('.categories a')
        category = ', '.join(a.text.strip() for a in category) if category else ''

        rating = card.select_one('.ratings .count')
        rating = rating.text.strip('()') if rating else ''

        street_name = card.select_one('.street-address')
        street_name = street_name.text.strip() if street_name else ''

        locality = card.select_one('.locality')
        locality = locality.text.strip() if locality else ''

        if locality:
            locality, region = locality.split(",") if ',' in locality else (locality, '')
            region, zipcode = region.strip().split() if ' ' in region.strip() else ('', '')
        else:
            locality, region, zipcode = '', '', ''

        business_info = {
            "Rank": rank,
            "Business Name": business_name,
            "Phone Number": phone_number,
            "Business Page": business_page,
            "Website": website,
            "Category": category,
            "Rating": rating,
            "Street Name": street_name,
            "Locality": locality,
            "Region": region,
            "Zipcode": zipcode
        }

        return business_info
        
        # After extracting the business page URL:
        website_content = self.scrape_emails_and_socials(business_page)  # Assuming business_page is the URL
        business_info.update(website_content)
        return business_info

    def scrape_emails_and_socials(self, website_url):
        if not website_url:
            return {"Emails": [], "Social Media": []}
        try:
            scrap = Scrapper(url=website_url, crawl=False)
            content = scrap.getText()
            IR = InfoReader(content=content)
            emails = IR.getEmails()
            socials = IR.getSocials()
            return {"Emails": emails, "Social Media": socials}
        except Exception as e:
            print(f"Error scraping {website_url}: {str(e)}")
            return {"Emails": [], "Social Media": []}

    def save_to_csv(self, data_list):
        # This line should be inside an instance method like this
        file_exists = os.path.isfile(self.file_path)  # Now 'self' correctly refers to the class instance

        fieldnames = [
            "Rank", "Business Name", "Phone Number", "Business Page", "Website",
            "Category", "Rating", "Street Name", "Locality", "Region", "Zipcode",
            "Emails", "discord", "youtube", "instagram", "twitter", "facebook",
            "linkedin", "github", "medium", "reddit", "pinterest", "tiktok"
        ]
        with open(self.file_path, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerows(data_list)

        self.total_businesses_collected += len(data_list)
        print(f"Total businesses collected so far: {self.total_businesses_collected}")

    def parse_page(self, content, location, data_list):
        soup = BeautifulSoup(content, "html.parser")
        all_cards = soup.select(".organic .srp-listing")
        result_count = soup.select_one('.showing-count')
        result_count = int(result_count.text.strip().split(' ')[-1]) if result_count else 0

        max_page = math.ceil(result_count/30)
        data_list = []

        if all_cards:
            for item in all_cards:
                result = self.extract_business_listing(item)
                data_list.append(result)
            self.save_to_csv(data_list)

        return max_page

    def fetch_html_content(self, page, location, max_retries=5, initial_wait_time=1, wait_time_multiplier=2, max_wait_time=60):
        params = {'search_terms': self.search_terms, 'geo_location_terms': location, 'page': page}
        url = self.base_url + '/search?' + urlencode(params, quote_via=quote_plus)
        retries = 0
        wait_time = initial_wait_time

        while retries < max_retries:
            try:
                response = requests.get(url, headers=self.headers, timeout=10)
                if response.status_code == 200:
                    return response.content
                else:
                    print(f"Error fetching page {page} for location {location}, status code: {response.status_code}")
            except requests.RequestException as e:
                print(f"Request failed: {str(e)}, retrying in {wait_time} seconds...")
            time.sleep(wait_time)
            retries += 1
            wait_time = min(wait_time * wait_time_multiplier, max_wait_time)

        print(f"Failed to fetch content after {max_retries} attempts.")
        return None

    def scrape_all_locations(self, locations):
        BATCH_SIZE = 30  # Number of businesses to process at once
        for location in locations:
            current_page = 1
            max_page = 1
            data_list = []  # Initialize the batch list
            while current_page <= max_page:
                print(f'Scraping data for page {current_page} in location: {location}')
                html_content = self.fetch_html_content(current_page, location)
                if html_content is None:
                    print(f"No html content for page {current_page} in location: {location}")
                    break
                else:
                    max_page = self.parse_page(html_content, location, data_list)  # Assuming this method updates data_list
                    if len(data_list) >= BATCH_SIZE:
                        self.process_batch(data_list)  # Process the current batch
                        data_list = []  # Reset the batch for the next set of businesses
                    current_page += 1
            if data_list:  # Don't forget to process the last batch if it's not empty
                self.process_batch(data_list)

    def process_batch(self, batch):
        enriched_data_list = []
        for business in batch:
            # Use the "Website" field from the business dictionary
            business_website = business.get("Website", "")
            if business_website:
                website_content = self.scrape_emails_and_socials(business_website)
                business.update(website_content)  # Enrich the business dictionary
            enriched_data_list.append(business)
        self.save_to_csv(enriched_data_list) 


def main():
    search_terms = input("Enter the search keyword: ")
    print("Enter locations separated by line breaks. Press Enter twice to start scraping.")
    
    locations_input = []
    while True:
        location_line = input()
        if location_line == "":
            break
        locations_input.append(location_line)

    file_name = f"{search_terms}_results.csv"
    scraper = YellowPageScraper(search_terms, file_path=file_name)
    try:
        scraper.scrape_all_locations(locations_input)
        print("Scraping completed successfully.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

        print(file_name)    

if __name__ == "__main__":
    main()
