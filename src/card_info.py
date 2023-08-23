"""Module containing pokemon card class"""
import re
import sqlite3
from functools import cached_property, total_ordering
from pathlib import Path
from pokemontcgsdk import Card


@total_ordering
class CardInfo:
    """Class representing a pokemon card"""

    name = None
    set_code = None
    collector_number = None
    regulation_mark = None
    supertype = None
    legality = {"standard": None, "expanded": None}
    quantity = None

    def __init__(
        self, *, name=None, set_code=None, collector_number=None, regulation_mark=None,
        supertype=None, quantity=None
    ):
        # set variables
        if name:
            self.name = str(name).strip()
        if set_code:
            self.set_code = str(set_code).strip().upper()
        if collector_number:
            self.collector_number = str(collector_number).strip().upper()
        if regulation_mark:
            self.regulation_mark = str(regulation_mark).strip().upper()
        if supertype:
            self.supertype = str(supertype).strip()
        if quantity:
            self.quantity = int(quantity)
        # ptcgl formats basic energy cards weird, we need to correct that
        if self.set_code == "ENERGY":
            self.name = self.name.removeprefix("Basic ")
            energy_symbols = {
                'G': "Grass", 'R': "Fire", 'W': "Water", 'L': "Lightning", 'P': "Psychic",
                'F': "Fighting", 'D': "Darkness", 'M': "Metal", 'Y': "Fairy"
            }
            for energy_symbol, energy_name in energy_symbols.items():
                self.name = re.sub(f"{{{energy_symbol}}}",
                                   f"{energy_name}", self.name)
            if not self.name.endswith(" Energy"):
                self.name += " Energy"
        # special treatment for basic energies
        basic_energies = [
            "Grass Energy", "Fire Energy", "Water Energy", "Lightning Energy", "Psychic Energy",
            "Fighting Energy", "Darkness Energy", "Metal Energy", "Fairy Energy"
        ]
        if self.name in basic_energies:
            self.set_code = "ENERGY"
        # limitless formats promos weird, we need to correct that
        if self.set_code.startswith("PR-"):
            self.collector_number = ''.join(
                [self.set_code.split('-')[-1], self.collector_number.rjust(3, '0')])
            self.set_code = "PR"

    def __eq__(self, other):
        if self.get_supertype == other.get_supertype:
            if self.get_supertype == "Trainer" or self.get_supertype == "Energy":
                if self.get_name == other.get_name:
                    return True
            else:
                if self.get_name == other.get_name and \
                   self.get_set_code == other.get_set_code and \
                   self.get_collector_number == other.get_collector_number:
                    return True
        return False

    def __lt__(self, other):
        return self.get_name < other.get_name

    def update_from_database(self, result):
        """Updates this object with information from local card database"""
        self.regulation_mark = result[0]
        self.supertype = result[1]
        self.legality["standard"] = result[2]
        self.legality["expanded"] = result[3]
        if not self.collector_number:
            self.collector_number = str(result[4]).strip().upper()

    def query_database(self, query, query_data):
        """Queries local database for card information"""
        conn = sqlite3.connect(Path(__file__).parent.resolve() / "cards.db")
        cursor = conn.cursor()
        results = cursor.execute(query, tuple(query_data)).fetchall()
        conn.close()
        if len(results) == 1:
            self.update_from_database(results[0])
            return True
        if len(results) > 1:
            supertype = results[0][1]
            if supertype in ["Trainer", "Energy"]:
                self.update_from_database(results[0])
                return True
        return False

    def lookup_from_database(self):
        """Creates and runs queries to get card information from local database"""
        query_root = "SELECT regMark, type, isStandardLegal, isExpandedLegal, collNo "\
                     "FROM cards WHERE "
        if self.name and self.set_code and self.collector_number:
            query = query_root + "name=? AND setCode=? AND collNo=?"
            query_data = [self.name, self.set_code, self.collector_number]
            if self.query_database(query, query_data):
                return True
        if self.set_code and self.collector_number:
            query = query_root + "setCode=? AND collNo=?"
            query_data = [self.set_code, self.collector_number]
            if self.query_database(query, query_data):
                return True
        if self.name and self.set_code:
            query = query_root + "name=? AND setCode=?"
            query_data = [self.name, self.set_code]
            if self.query_database(query, query_data):
                return True
        if self.name:
            query = query_root + "name=?"
            query_data = [self.name]
            if self.query_database(query, query_data):
                return True
        if self.name and self.set_code:
            query = query_root + "name=?"
            query_data = [' '.join([self.name, self.set_code])]
            if self.query_database(query, query_data):
                return True
        # if we still haven't foind it locally, try the API
        api_success = self.lookup_from_api()
        # if it was found by the API, save it locally
        if api_success:
            conn = sqlite3.connect(
                Path(__file__).parent.resolve() / "cards.db")
            cursor = conn.cursor()
            query = "INSERT INTO cards "\
                    "(name, setCode, collNo, regMark, type, isStandardLegal, isExpandedLegal) "\
                    "VALUES (?, ?, ?, ?, ?, ?, ?)"
            cursor.execute(query, (
                self.name, self.set_code, self.collector_number, self.regulation_mark,
                self.supertype, self.legality["standard"], self.legality["expanded"]
            ))
            conn.commit()
            conn.close()
        return api_success

    def update_from_api(self, card):
        """Updates this object with information from remote card API"""
        if not self.name:
            self.name = card.name
        if not self.set_code:
            self.set_code = card.set.ptcgoCode
        if not self.collector_number:
            self.collector_number = card.number
        if not self.regulation_mark:
            if card.regulationMark:
                self.regulation_mark = card.regulationMark
            else:
                self.regulation_mark = "NA"
        if not self.supertype:
            self.supertype = card.supertype
        if not self.legality["standard"]:
            self.legality["standard"] = card.legalities.standard == "Legal"
        if not self.legality["expanded"]:
            self.legality["expanded"] = card.legalities.expanded == "Legal"

    def query_api(self, search):
        """Queries remote API for card information"""
        cards = Card.where(q=search, orderBy='-set.releaseDate')
        if len(cards) == 1:
            self.update_from_api(cards[0])
            return True
        if len(cards) > 1:
            card = cards[0]
            if card.supertype in ["Trainer", "Energy"]:
                self.update_from_api(card)
                return True
        return False

    def lookup_from_api(self):
        """Creates and runs queries to get card information from remote API"""
        # clean the data
        set_ids = {"PR-SV": "svp", "SVI": "sv1", "PAL": "sv2", "OBF": "sv3"}
        set_code = self.set_code
        if set_code in set_ids:
            set_code = set_ids[set_code]
            set_search = 'set.id'
        else:
            set_search = 'set.ptcgoCode'
        collector_number = self.collector_number
        if collector_number:
            collector_number = collector_number.lstrip("0")
        # start querying API
        if self.name and set_code and collector_number:
            search = f'!name:"{self.name}" {set_search}:"{set_code}" number:*{collector_number}'
            if self.query_api(search):
                return True
        if set_code and collector_number:
            search = f'{set_search}:"{set_code}" number:*{collector_number}'
            if self.query_api(search):
                return True
        if self.name and set_code:
            search = f'!name:"{self.name}" {set_search}:"{set_code}"'
            if self.query_api(search):
                return True
        if self.name:
            search = f'!name:"{self.name}"'
            if self.query_api(search):
                return True
        if self.name and set_code:
            search = f'!name:"{self.name} {set_code}"'
            if self.query_api(search):
                return True
        return False

    @cached_property
    def get_name(self):
        """gets this card's name"""
        if not self.name:
            self.lookup_from_database()
        return self.name

    @cached_property
    def get_set_code(self):
        """gets this card's set code"""
        if not self.set_code:
            self.lookup_from_database()
        return self.set_code

    @cached_property
    def get_collector_number(self):
        """gets this card's collector number"""
        if not self.collector_number:
            self.lookup_from_database()
        return self.collector_number

    @cached_property
    def get_supertype(self):
        """gets this card's supertype"""
        if not self.supertype:
            self.lookup_from_database()
        return self.supertype

    @cached_property
    def get_regulation_mark(self):
        """gets this card's regulation mark"""
        if not self.regulation_mark:
            self.lookup_from_database()
        return self.regulation_mark

    @cached_property
    def get_standard_legality(self):
        """gets this card's standard legality"""
        if not self.legality["standard"]:
            self.lookup_from_database()
        return self.legality["standard"]

    @cached_property
    def get_expanded_legality(self):
        """gets this card's expanded legality"""
        if not self.legality["expanded"]:
            self.lookup_from_database()
        return self.legality["expanded"]
