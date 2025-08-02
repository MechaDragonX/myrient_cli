import aiohttp
import asyncio
import os
import re
import sys
from thefuzz import fuzz, process
import urllib.parse as urlparse
from database import Database

class UI():
    db = Database('https://myrient.erista.me/files/No-Intro/Sega%20-%20SG-1000/')


    @staticmethod
    async def download_async(session, filename, url):
        print(f'Downloading: {filename}')
        try:
            async with session.get(url, headers=UI.db.headers) as response:
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


    @staticmethod
    async def download_files(paths):
        async with aiohttp.ClientSession() as session:
            tasks = []
            for filename in paths:
                tasks.append(UI.download_async(session, filename, UI.db.games[filename][0]))
            await asyncio.gather(*tasks)


    # Return value:
    # [title string, plus tags list, minus tags list]
    @staticmethod
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
                    plus_tags.append(UI.db.short2tag[tag[1:]])
                elif '-' in tag:
                    minus_tags.append(UI.db.short2tag[tag[1:]])

            return [re.findall(query_regex, query)[0][1:-1], plus_tags, minus_tags]
        # Otherwise, return blanks for tag lists
        else:
            return [re.findall(query_regex, query)[0][1:-1], [], []]


    @staticmethod
    def check_result(result, plus_tags, minus_tags):
        # Check if the matches are close enough (if query is not blank), and check if the tags match
        plus_tags_found = False
        minus_tags_not_found = False

        # If result is a match tuple
        if type(result) == tuple:
            # Check if closeness score is >= 70
            if result[1] >= 70:
                if plus_tags and minus_tags:
                    # Check if any of the plus tags provided are in the result's tag list
                    plus_tags_found = any(item in UI.db.games[result[0]][2] for item in plus_tags)
                    minus_tags_not_found = set(minus_tags).isdisjoint(UI.db.games[result[0]][2])
            # Do not return anything if the closeness score is too low
            else:
                return None
        else:
            if plus_tags and minus_tags:
                # Check if any of the plus tags provided are in the result's tag list
                plus_tags_found = any(item in UI.db.games[result][2] for item in plus_tags)
                # Check if any of the minus tags provided ARE NOT in the result's tag list
                minus_tags_not_found = set(minus_tags).isdisjoint(UI.db.games[result][2])

        # Check if the tags lists aren't blank
        if plus_tags and minus_tags:
            # If both checks are not true, don't return result
            if not (plus_tags_found and minus_tags_not_found):
                return None

        # Return result as befits type
        if type(result) == tuple:
            return result[0]
        else:
            return result


    @staticmethod
    def search(query, plus_tags, minus_tags):
        matches = []
        # If the query isn't blank, run comparisons
        if query != "":
            # Find 30 results in the keys with partial matching
            # Returns tuple of (result string, closeness score int)
            matches = process.extract(query, UI.db.games.keys(), limit=30, scorer=fuzz.partial_ratio)
        # Otherwise, just look through everything
        else:
            matches = UI.db.games.keys()

        # Check if the matches are close enough (if query is not blank), and check if the tags match
        result = []
        results = []
        for match in matches:
            result = UI.check_result(match, plus_tags, minus_tags)
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


    @staticmethod
    def search_user_input():
        query = ''
        query_regex = r'"[^"]*"'
        parsed_query = []
        search_results = []

        while query == '':
            query = input('Please type your query: ').strip()
            if re.findall(query_regex, query):
                parsed_query = UI.parse_search_query(query)
                # Store results so they can be downloaded
                search_results = UI.search(parsed_query[0], parsed_query[1], parsed_query[2])
                input('<Press any key to continue>').strip()
                print()
            else:
                query = ''
                print('You need to surround your query in quotation marks!')

        # return search results since they're created once you reach end of function
        return search_results


    @staticmethod
    def gen_dl_list(search_results, queries):
        num_query = 0
        final_request = []

        for query in queries:
            num_query = int(query)
            if num_query > 0 and num_query <= len(search_results):
                final_request.append(search_results[num_query - 1])

        return final_request


    @staticmethod
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
                if filename != '' and filename in UI.db.games:
                    asyncio.run(UI.download_files([filename]))
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
                    asyncio.run(UI.download_files(search_results))
                elif query.isdigit() or len(re.findall(multi_dl_regex, query)) != 0:
                    asyncio.run(UI.download_files(UI.gen_dl_list(search_results, query.split(' '))))
                else:
                    query = ''
                    print(f'You either need the number of the file you wish to download, or "all" to download eveything!')


    @staticmethod
    def start():
        if os.path.isfile('sg1000-games.json'):
            UI.db.import_json_data('sg1000')
            print()
        else:
            UI.db.import_json_data('sg1000')
            UI.db.create_games_json('sg1000')
            UI.db.import_json_data('sg1000')
            os.system('clear||cls')


    @staticmethod
    def program():
        os.system('clear||cls')
        UI.start()

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
                    search_results = UI.search_user_input()
                case 'download' | 'dl' | 'd':
                    UI.download_user_input(search_results, filename, num_query)
                    # Reset search_results
                    search_results = []
                    input('<Press any key to continue>')
                    # Clear screan as results need not be on screen anymore
                    os.system('clear||cls')
