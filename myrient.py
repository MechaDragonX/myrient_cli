import aiohttp
import asyncio
from thefuzz import fuzz, process


class Myrient():
    def __init__(self, db):
        self.db = db


    async def download_async(self, session, filename, url):
        print(f'Downloading: {filename}')
        try:
            async with session.get(url, headers=self.db.headers) as response:
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


    async def download_files(self, paths):
        async with aiohttp.ClientSession() as session:
            tasks = []
            for filename in paths:
                tasks.append(self.download_async(session, filename, self.db.games[filename][0]))
            await asyncio.gather(*tasks)


    def check_result(self, result, plus_tags, minus_tags):
        # Check if the matches are close enough (if query is not blank), and check if the tags match
        plus_tags_found = False
        minus_tags_not_found = False

        # If result is a match tuple
        if type(result) == tuple:
            # Check if closeness score is >= 70
            if result[1] >= 70:
                if plus_tags or minus_tags:
                    # Check if the list is not empty
                    if plus_tags:
                        # Check if any of the plus tags provided are in the result's tag list
                        plus_tags_found = any(item in self.db.games[result[0]][2] for item in plus_tags)
                    else:
                        # If empty, treat this check as true
                        plus_tags_found = True
                    # Do the same with minus tags
                    if minus_tags:
                        minus_tags_not_found = set(minus_tags).isdisjoint(self.db.games[result[0]][2])
                    else:
                        minus_tags_not_found = False
            # Do not return anything if the closeness score is too low
            else:
                return None
        else:
            if plus_tags or minus_tags:
                # Check if any of the plus tags provided are in the result's tag list
                plus_tags_found = any(item in self.db.games[result][2] for item in plus_tags)
                # Check if any of the minus tags provided ARE NOT in the result's tag list
                minus_tags_not_found = set(minus_tags).isdisjoint(self.db.games[result][2])

        # Check if the tags lists aren't blank
        if plus_tags or minus_tags:
            # If both checks are not true, don't return result
            if not (plus_tags_found and minus_tags_not_found):
                return None

        # Return result as befits type
        if type(result) == tuple:
            return result[0]
        else:
            return result


    def search(self, query, plus_tags, minus_tags):
        matches = []
        # If the query isn't blank, run comparisons
        if query != "":
            # Find 30 results in the keys with partial matching
            # Returns tuple of (result string, closeness score int)
            matches = process.extract(query, self.db.games.keys(), limit=30, scorer=fuzz.partial_ratio)
        # Otherwise, just look through everything
        else:
            matches = list(self.db.games.keys())

        # Check if the matches are close enough (if query is not blank), and check if the tags match
        result = []
        results = []
        for match in matches:
            result = self.check_result(match, plus_tags, minus_tags)
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
