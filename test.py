import aiohttp
import asyncio
from bs4 import BeautifulSoup, Tag
import json
import os
import os.path
import re
import requests
import sys
from thefuzz import fuzz, process
import urllib.parse as urlparse


# Not provided
BASE_URL = 'https://myrient.erista.me/files/No-Intro/Sega%20-%20SG-1000/'
HEADERS = {
    'Referer': BASE_URL,
    'User-Agent': 'Mozilla/5.0',
}
EXTENSION = '.zip'

# filename: [
#   url,
#   title,
#   tags (list)
# ]
games = {}

TAGS = {
    'Region': [
        'Australia',
        'Europe',
        'France',
        'Japan',
        'Korea',
        'New Zealand',
        'Taiwan'
    ],
    'Language': [
        'En',
        'Ja',
        'Chinese Logo',
        'English Logo',
        'Korean Logo'
    ],
    'Platform': [
        'SC-3000',
        'SF-7000',
        'Othello Multivision'
    ],
    'Software Type': [
        'BIOS',
        'Program',
        'Unl'
    ],
    'Revision': [
        'Proto',
        'Rev 1',
        'Rev 2'
    ],
    'Dump Type': [
        'Alt'
    ]
}

SHORT2TAG = {
    'au': 'Australia',
    'eu': 'Europe',
    'fr': 'France',
    'jp': 'Japan',
    'kr': 'Korea',
    'nz': 'New Zealand',
    'tw': 'Taiwan',
    'en': 'En',
    'ja': 'Ja',
    'zh-logo': 'Chinese Logo',
    'en-logo': 'English Logo',
    'kr-logo': 'Korean Logo',
    'sc3k': 'SC-3000',
    'sf7k': 'SF-7000',
    'othello': 'Othello Multivision',
    'bios': 'BIOS',
    'prog': 'Program',
    'unl': 'Unl',
    'proto': 'Proto',
    'r1': 'Rev 1',
    'r2': 'Rev 2',
    'alt': 'Alt'
}


def get_all_hrefs():
    print(f'Fetching: {urlparse.unquote(BASE_URL)}')
    try:
        with requests.get(BASE_URL) as response:
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
                    if href.lower().endswith(EXTENSION):
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
def get_title_and_tags(filename):
    tag_regex = r'(?<=\().*?(?=\))'
    matches = re.findall(tag_regex, filename)

    split_tags = []
    tags = []
    all_tags = [item for sublist in TAGS.values() for item in sublist]
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

    tags.sort()
    if subtitle == '':
        return [filename[:filename.find('(') - 1], tags]
    else:
        return [title, tags]


async def get_file_info(session, href):
    # Full URL
    file_url = urlparse.urljoin(BASE_URL, href)
    # Filename from the href
    filename = urlparse.unquote(os.path.basename(href))

    title_and_tags = []
    # Make sure the file exists
    try:
        async with session.get(file_url, headers=HEADERS) as response:
            if response.status == 200:
                title_and_tags = get_title_and_tags(filename)
                games[filename] = [
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


async def get_all_links(hrefs):
    global games

    async with aiohttp.ClientSession() as session:
        tasks = [get_file_info(session, href) for href in hrefs]
        await asyncio.gather(*tasks)
        games = dict(sorted(games.items()))


def write_games_json(platform):
    print(f'Writing: {platform}.json')
    with open(f'{platform}.json', 'w') as file:
        json.dump(games, file, indent=4)
        file.write('\n')
    print(f'Wrote: {platform}.json')


def read_games_json(platform):
    global games

    print(f'Reading: {platform}.json')
    with open(f'{platform}.json', 'r') as file:
        games = json.load(file)
    print(f'Read: {platform}.json')


async def download_async(session, filename, url):
    print(f'Downloading: {filename}')
    try:
        async with session.get(url, headers=HEADERS) as response:
            # Check for error
            if response.status != 200:
                print(f'HTTP error for {filename}: {response.status}')
                return

            # Write in chunks
            with open(filename, 'wb') as file:
                async for chunk in response.content.iter_chunked(8192):
                    # Check if chunk is not empty
                    if chunk:
                        file.write(chunk)

        print(f'Saved: {filename}')

    except aiohttp.ClientError as error:
        print(f'Request error for {filename}: {error}')


async def download_files(paths):
    async with aiohttp.ClientSession() as session:
        tasks = []
        for filename in paths:
            tasks.append(download_async(session, filename, games[filename][0]))
        await asyncio.gather(*tasks)


# Return value:
# [title string, plus tags list, minus tags list]
def parse_search_query(query):
    tag_regex = r'"[^"]*"(.*)'
    query_regex = r'"[^"]*"'

    # Find everything in title that's not in quotes
    non_title = re.findall(tag_regex, query)[0][1:]
    # If there are no plus and minus tags
    if '+' in non_title or '-' in non_title:
        all_tags = non_title.split(' ')

        # Add them to seperate tags based on the first char
        plus_tags = []
        minus_tags = []
        for tag in all_tags:
            if '+' in tag:
                plus_tags.append(SHORT2TAG[tag[1:]])
            elif '-' in tag:
                minus_tags.append(SHORT2TAG[tag[1:]])

        return [re.findall(query_regex, query)[0][1:-1], plus_tags, minus_tags]
    # Otherwise, return blanks for tag lists
    else:
        return [re.findall(query_regex, query)[0][1:-1], [], []]


def check_result(result, plus_tags, minus_tags):
    # Check if the matches are close enough (if query is not blank), and check if the tags match
    plus_tags_found = False
    minus_tags_not_found = False

    # If result is a match tuple
    if type(result) == tuple:
        # Check if closeness score is >= 70
        if result[1] >= 70:
            # Check if any of the plus tags provided are in the result's tag list
            plus_tags_found = any(item in games[result[0]][2] for item in plus_tags)
            minus_tags_not_found = set(minus_tags).isdisjoint(games[result[0]][2])
    else:
        # Check if any of the plus tags provided are in the result's tag list
        plus_tags_found = any(item in games[result][2] for item in plus_tags)
        # Check if any of the minus tags provided ARE NOT in the result's tag list
        minus_tags_not_found = set(minus_tags).isdisjoint(games[result][2])

    # If both checks are true, then return result
    if plus_tags_found and minus_tags_not_found:
        if type(result) == tuple:
            return result[0]
        else:
            return result
    else:
        return None


def search(query, plus_tags, minus_tags):
    matches = []
    # If the query isn't blank, run comparisons
    if query != "":
        # Find 30 results in the keys with partial matching
        # Returns tuple of (result string, closeness score int)
        matches = process.extract(query, games.keys(), limit=30, scorer=fuzz.partial_ratio)
    # Otherwise, just look through everything
    else:
        matches = games.keys()

    # Check if the matches are close enough (if query is not blank), and check if the tags match
    result = []
    results = []
    for match in matches:
        result = check_result(match, plus_tags, minus_tags)
        if result != None:
            results.append(result)

    # Print the results
    print(f'Results:')
    if results:
        for i in range(len(results)):
            print(f'{i + 1}. {results[i]}')
    else:
        print('No results found')

    # Return for use later
    return results


def search_user_input():
    query = ''
    query_regex = r'"[^"]*"'
    parsed_query = []
    search_results = []

    while query == '':
        query = input('Please type your query: ').strip()
        if re.findall(query_regex, query):
            parsed_query = parse_search_query(query)
            # Store results so they can be downloaded
            search_results = search(parsed_query[0], parsed_query[1], parsed_query[2])
            input('<Press any key to continue>').strip()
            print()
        else:
            query = ''
            print('You need to surround your query in quotation marks!')

    # return search results since they're created once you reach end of function
    return search_results


def gen_dl_list(search_results, queries):
    num_query = 0
    final_request = []

    for query in queries:
        num_query = int(query)
        if num_query > 0 and num_query <= len(search_results):
            final_request.append(search_results[num_query - 1])

    return final_request


def download_user_input(search_results, filename, query):
    filename = ''
    query = ''
    num_query = 0
    multi_dl_regex = r'^(?:\d+ )+\d+'

    # If nothing was searched
    if not search_results:
        while filename != '':
            # Ask for filename
            filename = input('Please type the name of the file you wish to download: ').strip()
            if filename != '' and filename in games:
                asyncio.run(download_files([filename]))
                print()
            else:
                filename = ''
                print('That file doesn\'t exist!\n')
    # Otherwise
    else:
        # Ask for number of search result
        while query == '':
            query = input('Please type the number of the result you wish to download: ').strip()
            # if query.isdigit():
            #     num_query = int(query)
            #     if num_query > 0 and num_query <= len(search_results):
            #         asyncio.run(download_files([search_results[num_query - 1]]))
            #     else:
            #         query = ''
            #         print(f'You need to type a number between 1 and {len(search_results)}')
            # else:
            if query.lower() == 'all':
                asyncio.run(download_files(search_results))
            elif query.isdigit() or len(re.findall(multi_dl_regex, query)) != 0:
                asyncio.run(download_files(gen_dl_list(search_results, query.split(' '))))
            else:
                query = ''
                print(f'You either need the number of the file you wish to download, or "all" to download eveything!')


def create_games_json():
    asyncio.run(get_all_links(get_all_hrefs()))
    write_games_json('sg1000')


def start():
    if os.path.isfile('sg1000.json'):
        read_games_json('sg1000')
        print()
    else:
        create_games_json()
        os.system('clear||cls')


os.system('clear||cls')
start()

command = ''
query = ''
parsed_query = []
search_results = []
filename = ''
num_query = 0
while command.lower().strip() != 'q' or command.lower().strip() != 'quit':
    command = input('Please type a command: ').lower().strip()
    match command:
        case 'search' | 's':
            search_results = search_user_input()
        case 'download' | 'dl' | 'd':
            download_user_input(search_results, filename, num_query)
            # Reset search_results
            search_results = []
            input('<Press any key to continue>')
            # Clear screan as results need not be on screen anymore
            os.system('clear||cls')
