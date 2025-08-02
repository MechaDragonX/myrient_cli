import sys
from database import Database
from myrient import Myrient
from ui import UI


base_url = ''
platform = ''

if len(sys.argv) != 2:
    print('You must provide a platform name!')
else:
    # Platform: Sega SG-1000
    if sys.argv[1] == 'sg1000':
        base_url = 'https://myrient.erista.me/files/No-Intro/Sega%20-%20SG-1000/'
        platform = 'sg1000'
    # Platform: Epoch Super Casette Vision
    elif sys.argv[1] == 'scv':
        base_url = 'https://myrient.erista.me/files/No-Intro/Epoch%20-%20Super%20Cassette%20Vision/'
        platform = 'scv'

db = Database(base_url)
ui = UI(db, Myrient(db))
ui.program(platform)
