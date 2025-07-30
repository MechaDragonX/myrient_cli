import aiohttp
import asyncio
import requests
from bs4 import BeautifulSoup, Tag
import os
import sys
import urllib.parse as urlparse


# Not provided
BASE_URL = ''
HEADERS = {
    "Referer": BASE_URL,
    "User-Agent": "Mozilla/5.0",
}
EXTENSION = '.zip'

# filename: url
files = {}


def get_all_hrefs():
    print(f'Fetching: {urlparse.unquote(BASE_URL)}')
    try:
        with requests.get(BASE_URL) as response:
            response.raise_for_status()

            parser = BeautifulSoup(response.text, 'html.parser')
            hrefs = []
            # a tags for links
            for a in parser.find_all('a'):
                # Make sure is proper link with href attribute
                if hasattr(a, 'get') and isinstance(a, Tag):
                    href = a.get('href')
                    # Check if extension is a zip file
                    if href.lower().endswith(EXTENSION):
                        hrefs.append(href)

            return hrefs
    # HTTP error code error, like 404
    except requests.exceptions.HTTPError as error:
        print(f'HTTP error: {error}')
    # Network error such as timeout
    except requests.exceptions.RequestException as error:
        print(f'Other error: {error}')


async def get_file_info(session, href):
    # Full URL
    file_url = urlparse.urljoin(BASE_URL, href)
    # Filename from the href
    filename = urlparse.unquote(os.path.basename(href))

    # Make sure the file exists
    try:
        async with session.get(file_url, headers=HEADERS) as response:
            if response.status == 200:
                files[filename] = file_url
                print(f"Found: {filename}")
            else:
                print(f"Skipped (HTTP {response.status}): {filename}")
    except aiohttp.ClientError as error:
        print(f"Network error for {filename}: {error}")


async def get_all_links(hrefs):
    async with aiohttp.ClientSession() as session:
        tasks = [get_file_info(session, href) for href in hrefs]
        await asyncio.gather(*tasks)


async def download_async(session, filename, url):
    try:
        async with session.get(url, headers=HEADERS) as response:
            # Check for error
            if response.status != 200:
                print(f"HTTP error for {filename}: {response.status}")
                return

            # Write in chunks
            with open(filename, 'wb') as file:
                async for chunk in response.content.iter_chunked(8192):
                    # Check if chunk is not empty
                    if chunk:
                        file.write(chunk)

        print(f"Saved: {filename}")

    except aiohttp.ClientError as error:
        print(f"Request error for {filename}: {error}")


async def download_files(paths):
    async with aiohttp.ClientSession() as session:
        tasks = []
        for filename in paths:
            tasks.append(download_async(session, filename, files[filename]))
        await asyncio.gather(*tasks)


if len(sys.argv) != 2 and not sys.argv[1].endswith(EXTENSION):
    print("Error: No filename provided!")
else:
    asyncio.run(get_all_links(get_all_hrefs()))
    asyncio.run(download_files([sys.argv[1]]))
