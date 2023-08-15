import logging
import re
import sqlite3
from functools import total_ordering
from pathlib import Path
from pokemontcgsdk import Card

@total_ordering
class cardInfo:
    name = None
    set = None
    collNo = None
    regMark = None
    type = None
    isStandardLegal = None
    isExpandedLegal = None
    quantity = None

    def __init__(self, *, name=None, set = None, collNo = None, regMark = None, type = None, quantity = None):
        #set variables
        if name:
            self.name = str(name).strip()
        if set:
            self.set = str(set).strip().upper()
        if collNo:
            self.collNo = str(collNo).strip().upper()
        if regMark:
            self.regMark = str(regMark).strip().upper()
        if type:
            self.type = str(type).strip()
        if quantity:
            self.quantity = int(quantity)
        #ptcgl formats basic energy cards weird, we need to correct that
        if self.set == "ENERGY":
            self.name = self.name.removeprefix("Basic ")
            energySymbols = {'G': "Grass", 'R': "Fire", 'W': "Water", 'L': "Lightning", 'P': "Psychic", 'F': "Fighting", 'D': "Darkness", 'M': "Metal", 'Y': "Fairy"}
            for symbol in energySymbols:
                self.name = re.sub(f"{{{symbol}}}", f"{energySymbols[symbol]}", self.name)
            if not self.name.endswith(" Energy"):
                self.name += " Energy"
        #special treatment for basic energies
        if self.name in ["Grass Energy", "Fire Energy", "Water Energy", "Lightning Energy", "Psychic Energy", "Fighting Energy", "Darkness Energy", "Metal Energy", "Fairy Energy"]:
            self.set = "ENERGY"
        #limitless formats promos weird, we need to correct that
        if self.set.startswith("PR-"):
            self.collNo = ''.join([self.set.split('-')[-1], self.collNo.rjust(3, '0')])
            self.set = "PR"

    def __eq__(self, other):
        if self.getType() == other.getType():
            if self.getType() == "Trainer" or self.getType() == "Energy":
                return self.getName() == other.getName()
            else:
                return self.getName() == other.getName() and self.getSet() == other.getSet() and self.getCollNo() == other.getCollNo()
        return False
    
    def __lt__(self, other):
        return self.getName() < other.getName()

    def dbUpdate(self, results):
        self.regMark = results[0][0]
        self.type = results[0][1]
        self.isStandardLegal = results[0][2]
        self.isExpandedLegal = results[0][3]

    def dbQuery(self, query, queryData):
        conn = sqlite3.connect(Path(__file__).parent.resolve() / "cards.db")
        cursor = conn.cursor()
        results =  cursor.execute(query, tuple(queryData)).fetchall()
        conn.close()
        if len(results) == 1:
            self.dbUpdate(results=results)
            return True
        elif len(results) > 1:
            type = results[0][1]
            if type in ["Trainer", "Energy"]:
                self.dbUpdate(results=results)
                return True
        return False
    
    def dbLookup(self):
        queryRoot = "SELECT regMark, type, isStandardLegal, isExpandedLegal FROM cards WHERE "
        if self.name and self.set and self.collNo:
            query = queryRoot + "name=? AND setCode=? AND collNo=?"
            queryData = [self.name, self.set, self.collNo]
            if self.dbQuery(query=query, queryData=queryData):
                return True
        if self.set and self.collNo:
            query = queryRoot + "setCode=? AND collNo=?"
            queryData = [self.set, self.collNo]
            if self.dbQuery(query=query, queryData=queryData):
                return True
        if self.name:
            query = queryRoot + "name=?"
            queryData = [self.name]
            if self.dbQuery(query=query, queryData=queryData):
                return True
        #if we still haven't foind it locally, try the API
        apiSuccess = self.apiLookup()
        #if it was found by the API, save it locally
        if apiSuccess:
            conn = sqlite3.connect(Path(__file__).parent.resolve() / "cards.db")
            cursor = conn.cursor()
            query = "INSERT INTO cards (name, setCode, collNo, regMark, type, isStandardLegal, isExpandedLegal) VALUES (?, ?, ?, ?, ?, ?, ?)"
            cursor.execute(query, (self.name, self.set, self.collNo, self.regMark, self.type, self.isStandardLegal, self.isExpandedLegal))
            conn.commit()
            conn.close()
        return apiSuccess

    def apiUpdate(self, card):
        if not self.name:
            self.name = card.name
        if not self.set:
            self.set = card.set.ptcgoCode
        if not self.collNo:
            self.collNo = card.number
        if not self.regMark:
            if card.regulationMark:
                self.regMark = card.regulationMark
            else:
                self.regMark = "NA"
        if not self.type:
            self.type = card.supertype
        if not self.isStandardLegal:
            self.isStandardLegal = card.legalities.standard == "Legal"
        if not self.isExpandedLegal:
            self.isExpandedLegal = card.legalities.expanded == "Legal"

    def apiQuery(self, search):
        cards = Card.where(q=search, orderBy='-set.releaseDate')
        if len(cards) == 1:
            self.apiUpdate(cards[0])
            return True
        elif len(cards) > 1:
            card = cards[0]
            if card.supertype in ["Trainer", "Energy"]:
                self.apiUpdate(card)
                return True
        return False

    def apiLookup(self):
        #clean the data
        setIDs = {"PR-SV":"svp", "SVI":"sv1", "PAL":"sv2", "OBF":"sv3"}
        if self.set:
            set = self.set
            if set in setIDs:
                set = setIDs[set]
                setSearch = 'set.id'
            else:
                setSearch = 'set.ptcgoCode'
        if self.collNo:
            number = self.collNo.lstrip("0")
        #start querying API
        if self.name and set and number:
            search = f'!name:"{self.name}" {setSearch}:"{set}" number:*{number}'
            if self.apiQuery(search=search):
                return True
        if set and number:
            search = f'{setSearch}:"{set}" number:*{number}'
            if self.apiQuery(search=search):
                return True
        if self.name:
            search = f'!name:"{self.name}"'
            if self.apiQuery(search=search):
                return True
        return False

    def getName(self):
        if not self.name:
            self.dbLookup()
        return self.name
    
    def getSet(self):
        if not self.set:
            self.dbLookup()
        return self.set
    
    def getCollNo(self):
        if not self.collNo:
            self.dbLookup()
        return self.collNo
    
    def getType(self):
        if not self.type:
            self.dbLookup()
        return self.type
    
    def getRegMark(self):
        if not self.regMark:
            self.dbLookup()
        return self.regMark

    def getStandardLegality(self):
        if not self.isStandardLegal:
            self.dbLookup()
        return self.isStandardLegal

    def getExpandedLegality(self):
        if not self.isExpandedLegal:
            self.dbLookup()
        return self.isExpandedLegal

    def getQuantity(self):
        return self.quantity