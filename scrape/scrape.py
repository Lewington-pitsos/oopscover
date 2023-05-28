import os
import requests
from bs4 import BeautifulSoup
from html2text import html2text
from urllib.parse import urljoin
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote

start_time = time.time()

save_dir = 'data/medicare/'

# Set the starting url
start_url = 'https://www.health.gov.au/topics/medicare/about/what-medicare-covers'

# Maintain a queue of urls to scrape next
url_queue = [start_url]

# Keep track of urls that have been scraped to avoid duplication
scraped_urls = set()

def scrape_url(url, url_queue):

    if url in scraped_urls:
        return

    try:
        # Make a request to the url
        response = requests.get(url)
        scraped_urls.add(quote(url))

        print(f'{len(url_queue)} urls left, scraping:', url)

        # Parse the response text with BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')

        # Convert the html to text
        text = html2text(str(soup))

        if 'medicare' in text.lower():
            # Save the text to a file, using the url as the filename
            filename = url.replace('https://', '').replace('http://', '').replace('/', '_') + '.txt'
            
            filename = save_dir + filename
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(text)  

            # Add the url to the set of urls that have been scraped

            with open(save_dir + 'url_mapping.txt', 'a') as f:
                f.write(url + ' ' + filename + '\n')

        # Find all links on the page and add them to the queue of urls to scrape
        for a_tag in soup.find_all('a'):
            href = a_tag.get('href')
            # Ensure the link is not None and is not a relative link
            if href and not href.startswith('#') and not href.startswith('mailto:'):
                # Complete the link if it is a relative link
                new_url = urljoin(url, href).split("?")[0].split("#")[0]
                if 'health.gov.au' in new_url and new_url not in scraped_urls:
                    url_queue.append(new_url)

    except Exception as e:
        print('Error scraping:', url)
        print(e)

# Set the maximum number of threads to use
max_threads = 10

def delete_files(directory):
    for file_name in os.listdir(directory):
        file_path = os.path.join(directory, file_name)
        if os.path.isfile(file_path):
            os.remove(file_path)
            print("Deleted:", file_path)

# Call the function to delete files
delete_files(save_dir)

url = url_queue.pop(0)
scrape_url(url, url_queue)


with ThreadPoolExecutor(max_workers=max_threads) as executor:
    while True:
        if len(url_queue) > 0:
            url = url_queue.pop(0)
            executor.submit(scrape_url, url, url_queue)
        else:
            if len(executor._threads) == 0:
                break
            else:
                time.sleep(1)

print('Number of urls scraped:', len(scraped_urls))
print('Time taken: {:.1f} seconds'.format(time.time() - start_time))
