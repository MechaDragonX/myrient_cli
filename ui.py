import asyncio
import os
import re

class UI():
    def __init__(self, db, myrient):
        self.db = db
        self.myrient = myrient


    # Return value:
    # [title string, plus tags list, minus tags list]
    def parse_search_query(self, query):
        tag_regex = r'"[^"]*"(.*)'
        query_regex = r'"[^"]*"'
        tag_list = [item for sublist in self.db.tags.values() for item in sublist]

        # Find everything in title that's not in quotes
        non_title = re.findall(tag_regex, query)[0][1:]
        # If there are no plus and minus tags
        if '+' in non_title or '-' in non_title:
            all_file_tags = non_title.split(' ')

            # Add them to seperate tags based on the first char
            full_tag = ''
            plus_tags = []
            minus_tags = []
            for tag in all_file_tags:
                if self.db.short2tag[tag[1:]] in tag_list:
                    full_tag = self.db.short2tag[tag[1:]]
                    if '+' in tag:
                        plus_tags.append(full_tag)
                    elif '-' in tag:
                        minus_tags.append(full_tag)

            return [re.findall(query_regex, query)[0][1:-1], plus_tags, minus_tags]
        # Otherwise, return blanks for tag lists
        else:
            return [re.findall(query_regex, query)[0][1:-1], [], []]


    def search_user_input(self):
        query = ''
        query_regex = r'"[^"]*"'
        parsed_query = []
        search_results = []

        while query == '':
            query = input('Please type your query: ').strip()
            if re.findall(query_regex, query):
                parsed_query = self.parse_search_query(query)
                # Store results so they can be downloaded
                search_results = self.myrient.search(parsed_query[0], parsed_query[1], parsed_query[2])
                input('<Press any key to continue>').strip()
                print()
            else:
                query = ''
                print('You need to surround your query in quotation marks!')

        # return search results since they're created once you reach end of function
        return search_results


    def gen_dl_list(self, search_results, queries):
        num_query = 0
        final_request = []

        for query in queries:
            num_query = int(query)
            if num_query > 0 and num_query <= len(search_results):
                final_request.append(search_results[num_query - 1])

        return final_request


    def download_user_input(self, search_results, filename, query):
        filename = ''
        query = ''
        num_query = 0
        multi_dl_regex = r'^(?:\d+ )+\d+'

        # If nothing was searched
        if not search_results:
            while filename != '':
                # Ask for filename
                filename = input('Please type the name of the file you wish to download: ').strip()
                if filename != '' and filename in self.db.games:
                    asyncio.run(self.myrient.download_files([filename]))
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
                    asyncio.run(self.myrient.download_files(search_results))
                elif query.isdigit() or len(re.findall(multi_dl_regex, query)) != 0:
                    asyncio.run(self.myrient.download_files(self.gen_dl_list(search_results, query.split(' '))))
                else:
                    query = ''
                    print(f'You either need the number of the file you wish to download, or "all" to download eveything!')


    def start(self, platform):
        # If database does not exist, generate it
        if not os.path.isfile(f'data/{platform}-games.json'):
            self.db.import_json_data(f'{platform}')
            self.db.create_games_json(f'{platform}')
        # Load database
        self.db.import_json_data(f'{platform}')
        os.system('clear||cls')


    def program(self, platform):
        os.system('clear||cls')
        self.start(platform)

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
                    search_results = self.search_user_input()
                case 'download' | 'dl' | 'd':
                    self.download_user_input(search_results, filename, num_query)
                    # Reset search_results
                    search_results = []
                    input('<Press any key to continue>')
                    # Clear screan as results need not be on screen anymore
                    os.system('clear||cls')
