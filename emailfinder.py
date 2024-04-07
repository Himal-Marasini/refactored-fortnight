import csv
import concurrent.futures
import glob
import sys
import requests
import re  # Import for regular expression operations
from requests.exceptions import ConnectionError, TooManyRedirects, Timeout
from modules.scrapper import Scrapper
from modules.info_reader import InfoReader

def detect_csv_files():
    """Find all CSV files in the current directory."""
    return glob.glob('*.csv')

def choose_csv_file(files):
    """Let the user select a CSV file if multiple are present."""
    for index, file in enumerate(files):
        print(f"{index + 1}: {file}")
    choice = int(input("Choose the CSV file number: ")) - 1
    return files[choice]

def ensure_http(url):
    """Ensure URLs start with http:// or https://."""
    if not url.startswith(('http://', 'https://')):
        return "http://" + url
    return url

def classify_social_links(social_links):
    """Organize social media links by platform."""
    platforms = ["discord", "youtube", "instagram", "twitter", "facebook", "linkedin", "github", "medium", "reddit", "pinterest", "tiktok"]
    social_media = {platform: "" for platform in platforms}
    for link in social_links:
        for platform in platforms:
            if platform in link:
                social_media[platform] = link
                break
    return social_media

def check_url_accessibility(url):
    """Check if a URL is accessible."""
    try:
        response = requests.head(url, allow_redirects=True, timeout=5)
        return response.status_code == 200
    except (ConnectionError, TooManyRedirects, Timeout):
        return False

def validate_and_select_email(emails):
    """Validate emails, clean up, and select the first valid email."""
    email_pattern = re.compile(r"[a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
    for email in emails:
        # Clean email by removing URL parameters or fragments
        clean_email = email.split('?')[0].split(';')[0]
        if email_pattern.match(clean_email):
            return clean_email
    return ""

def process_row(row):
    """Process each row, scraping URLs for emails and social media links."""
    url = row.get('Website', '')  # Change 'url' to 'Website'
    if not url or not check_url_accessibility(ensure_http(url)):
        return row, 0  # Skip if URL is empty or not accessible

    try:
        scrap = Scrapper(url=ensure_http(url))
        IR = InfoReader(content=scrap.getText())
        emails = IR.getEmails()
        valid_email = validate_and_select_email(emails)  # Validate and select a single email
        row.update({
            "Emails": valid_email,
            **classify_social_links(IR.getSocials())
        })
        return row, int(bool(valid_email))  # Return 1 if a valid email is found, 0 otherwise
    except Exception as e:
        print(f"Error processing {url}: {e}")
    return row, 0

def save_results_to_csv(output_file_path, fieldnames):
    """Create a CSV writer to save data in real-time."""
    return csv.DictWriter(open(output_file_path, 'w', newline='', encoding='utf-8'), fieldnames=fieldnames)

def main():
    # Check if a filename was provided as an argument
    if len(sys.argv) < 2:
        print("Usage: python3 emailfinder.py <CSV_FILENAME>")
        sys.exit(1)  # Exit the script indicating an error

    # The second command line argument is expected to be the CSV filename
    file_path = sys.argv[1]
    output_file_path = file_path.replace('.csv', '_enhanced.csv')

    processed_rows = 0
    email_count = 0

    with open(file_path, mode='r', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        fieldnames = reader.fieldnames + ['Emails'] + list(classify_social_links([]).keys())

        writer = save_results_to_csv(output_file_path, fieldnames)
        writer.writeheader()

        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(process_row, row) for row in reader]

            for future in concurrent.futures.as_completed(futures):
                result, emails_found = future.result()
                writer.writerow(result)
                processed_rows += 1
                email_count += emails_found
                print(f"Processed {processed_rows} rows, found {email_count} emails.")  # Update in real-time

    print(f"Processing complete. {processed_rows} rows processed with {email_count} emails found. Data saved to {output_file_path}.")

if __name__ == "__main__":
    main()
