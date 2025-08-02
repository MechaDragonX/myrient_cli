from database import Database
from myrient import Myrient
from ui import UI

db = Database('https://myrient.erista.me/files/No-Intro/Sega%20-%20SG-1000/')
ui = UI(db, Myrient(db))
ui.program('sg1000')
