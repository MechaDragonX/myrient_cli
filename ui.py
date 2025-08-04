import asyncio
import os
import re
import shlex

class UI():
    def __init__(self, db, myrient):
        self.db = db
        self.myrient = myrient


    def parse_tag(self, tag):
        if tag in self.db.tags.values():
            # return key
            return next((k for k, v in self.db.tags.items() if v == tag))
        elif tag in self.db.tags:
            return tag
        else:
            return None


    # Return value:
    # [title string, plus tags list, minus tags list]
    def parse_search_query(self, query_args):
        full_tag = ''
        plus_tags = []
        minus_tags = []
        # title search query
        title_query = ''
        incorrect_args = False
        for arg in query_args:
            if arg[0] in ('+', '-'):
                target_list = plus_tags if arg[0] == '+' else minus_tags
                full_tag = self.parse_tag(arg[1:])
                if full_tag is not None:
                    target_list.append(full_tag)
                else:
                    incorrect_args = True
            elif title_query == '':
                title_query = arg
            else:
                incorrect_args = True


        if incorrect_args:
            return None

        return [title_query, plus_tags, minus_tags]


    def search_user_input(self):
        query = ''
        query_regex = r'"[^"]*"'
        parsed_query = []
        search_results = []

        while query == '':
            query = input('Please type your query: ').strip()
            parsed_query = self.parse_search_query(shlex.split(query))
            if parsed_query != None:
                # Store results so they can be downloaded
                search_results = self.myrient.search(parsed_query[0], parsed_query[1], parsed_query[2])
                input('<Press any key to continue>').strip()
                print()
            else:
                query = ''
                print('You either need quotation marks around your query, or not all of your tags are supported!')

        # return search results since they're created once you reach end of function
        return search_results


    def gen_dl_list(self, search_results, queries):
        num_query = 0
        final_request = []

        for query in queries:
            num_query = int(query)
            if num_query > 0 and num_query <= len(search_results):
                final_request.append(search_results[num_query - 1])
            else:
                return None

        return final_request


    def download_user_input(self, search_results, filename):
        filename = ''
        query = ''
        multi_dl_regex = r'^(?:\d+ )+\d+'
        final_result = []

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
                if query.lower() == 'all':
                    asyncio.run(self.myrient.download_files(search_results))
                elif query.isdigit() or len(re.findall(multi_dl_regex, query)) != 0:
                    final_result = self.gen_dl_list(search_results, query.split(' '))
                    if final_result != None:
                        asyncio.run(self.myrient.download_files(final_result))
                    else:
                        query = ''
                        print(f'Make sure the numbers you type are within the list!')
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

        running = True
        command = ''
        query = ''
        parsed_query = []
        search_results = []
        filename = ''
        while running:
            command = input('Please type a command: ').lower().strip()
            match command:
                case 'search' | 's':
                    search_results = self.search_user_input()
                case 'download' | 'dl' | 'd':
                    self.download_user_input(search_results, filename)
                    # Reset search_results
                    search_results = []
                    input('<Press any key to continue>')
                    # Clear screan as results need not be on screen anymore
                    os.system('clear||cls')
                case 'quit' | 'q':
                    running = False

        print('Goodbye!')
