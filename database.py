import aiohttp
import asyncio
from bs4 import BeautifulSoup, Tag
import json
import os
import re
import requests
import urllib.parse as urlparse


class Database():
    def __init__(self, base_url):
        self.EXTENSION = '.zip'
        self.base_url = base_url
        self.headers = {
            'Referer': base_url,
            'User-Agent': 'Mozilla/5.0',
        }
        self.games = {}
        self.tags = {}


    def import_all_hrefs(self):
        print(f'Fetching: {urlparse.unquote(self.base_url)}')
        try:
            with requests.get(self.base_url) as response:
                response.raise_for_status()

                parser = BeautifulSoup(response.text, 'html.parser')
                hrefs = []
                href = None
                # a tags for links
                for a in parser.find_all('a'):
                    # Make sure is proper link with href attribute
                    if hasattr(a, 'get') and isinstance(a, Tag):
                        href = a.get('href')
                        # Check if extension is a zip file
                        if href.lower().endswith(self.EXTENSION):
                            hrefs.append(href)

                return hrefs
        # HTTP error code error, like 404
        except requests.exceptions.HTTPError as error:
            print(f'HTTP error: {error}')
        # Network error such as timeout
        except requests.exceptions.RequestException as error:
            print(f'Other error: {error}')


    # Return value:
    # List containing the title of the game and the tags
    # This is done at the same time to handle cases of parenthetical subtitles
    def import_title_and_tags(self, filename):
        tag_regex = r'(?<=\().*?(?=\))'
        matches = re.findall(tag_regex, filename)

        split_tags = []
        tags = []
        all_tags = list(self.tags.values())
        title = ''
        # For situations where the filename contains a parenthetical subtitle
        # Example: Kagaku (Gensokigou Master) (Japan) (SC-3000) (Program).zip
        # In this case, the title is 'Kagaku (Gensokigou Master)''
        # And the tags are [ 'Japan', 'Program', 'SC-3000' ]
        subtitle = ''
        for item in matches:
            if ',' in item:
                split_tags = item.split(', ')
                for tag in split_tags:
                    if item in all_tags:
                        tags.append(tag)
                split_tags = []
            elif item in all_tags:
                tags.append(item)
            else:
                subtitle = f'({item})'
                # Find the index where (subtitle) ends
                end_index = filename.find(subtitle) + len(subtitle)
                # Slice the string up to that point
                title = filename[:end_index]

        # Handle BIOS tag differently since it's written differntly
        if '[BIOS]' in filename:
            tags.append('BIOS')

        tags.sort()
        if subtitle == '':
            return [filename[:filename.find('(') - 1], tags]
        else:
            return [title, tags]


    async def import_file_info(self, session, href):
        # Full URL
        file_url = urlparse.urljoin(self.base_url, href)
        # Filename from the href
        filename = urlparse.unquote(os.path.basename(href))

        title_and_tags = []
        # Make sure the file exists
        try:
            async with session.get(file_url, headers=self.headers) as response:
                if response.status == 200:
                    title_and_tags = self.import_title_and_tags(filename)
                    self.games[filename] = [
                        file_url,
                        # Title
                        title_and_tags[0],
                        # List of tags sorted alphabetically
                        title_and_tags[1]
                    ]
                    print(f'Found: {filename}')
                else:
                    print(f'Skipped (HTTP {response.status}): {filename}')
        except aiohttp.ClientError as error:
            print(f'Network error for {filename}: {error}')


    async def import_all_links(self, hrefs):
        async with aiohttp.ClientSession() as session:
            tasks = [self.import_file_info(session, href) for href in hrefs]
            await asyncio.gather(*tasks)
            self.games = dict(sorted(self.games.items()))


    def write_games_json(self, platform):
        print(f'Writing: {platform}-games.json')
        with open(f'data/{platform}-games.json', 'w') as file:
            json.dump(self.games, file, indent=4)
            file.write('\n')
        print(f'Wrote: {platform}-games.json')


    def read_json(self, category, platform=''):
        if category == 'games':
            with open(f'data/{platform}-{category}.json', 'r') as file:
                self.games = json.load(file)
        else:
            with open(f'data/{category}.json', 'r') as file:
                self.tags = json.load(file)

    def create_games_json(self, platform):
        asyncio.run(self.import_all_links(self.import_all_hrefs()))
        self.write_games_json(platform)

    def import_json_data(self, platform):
        print(f'Reading database files')
        if not self.tags:
            self.read_json('tags')
        if os.path.isfile(f'data/{platform}-games.json'):
            self.read_json('games', platform)
        print(f'Database files read')
