import subprocess
from YPscraper import YellowPageScraper

class Orchestrator:
    def __init__(self):
        self.search_terms = None
        self.locations_input = []
        self.file_name = None

    def run_yp_scraper(self):
        self.search_terms = input("Enter the search keyword: ")
        print("Enter locations separated by line breaks. Press Enter twice to start scraping.")
        
        while True:
            location_line = input()
            if location_line == "":
                break
            self.locations_input.append(location_line)

        self.file_name = f"{self.search_terms}_results.csv"
        # Adjusting YellowPageScraper instantiation to match expected arguments
        scraper = YellowPageScraper(self.search_terms, file_path=self.file_name)
        try:
            # Assuming scrape_all_locations method exists and takes a list of locations as its argument
            scraper.scrape_all_locations(self.locations_input)
            print("Scraping completed successfully.")
        except Exception as e:
            print(f"An error occurred during scraping: {str(e)}")

    def run_email_finder(self):
        if self.file_name:  # Checks if the file_name is set, implying the scraper has run.
            try:
                # Assuming emailfinder.py accepts a filename as its first command-line argument
                subprocess.run(['python3', 'emailfinder.py', self.file_name])
                print("Email finder completed successfully.")
            except Exception as e:
                print(f"An error occurred in the email finder: {str(e)}")
        else:
            print("No file found to process with email finder.")

def main():
    orchestrator = Orchestrator()
    orchestrator.run_yp_scraper()
    orchestrator.run_email_finder()

if __name__ == "__main__":
    main()
