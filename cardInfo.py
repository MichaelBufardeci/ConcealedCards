import logging
import re
import sqlite3
from functools import total_ordering
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
            self.type = "Energy"
            self.name = self.name.removeprefix("Basic ")
            energySymbols = {'G': "Grass", 'W': "Water", 'R': "Fire", 'L': "Lightning", 'P': "Psychic", 'F': "Fighting", 'D': "Darkness", 'M': "Metal", 'Y': "Fairy"}
            for symbol in energySymbols:
                self.name = re.sub(f"{{{symbol}}}", f"{energySymbols[symbol]}", self.name)
            if not self.name.endswith(" Energy"):
                self.name += " Energy"
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

    def dbLookup(self):
        conn = sqlite3.connect("cards.db")
        cursor = conn.cursor()
        query = "SELECT regMark, type, isStandardLegal, isExpandedLegal FROM cards WHERE "
        queryData = []
        if self.name:
            query += "name=?"
            queryData.append(self.name)
        if self.set and self.collNo:
            if query.endswith("?"):
                query += " AND "
            query += "setCode=? AND collNo=?"
            queryData.append(self.set)
            queryData.append(self.collNo)
        if queryData:
            print(query)
            print(queryData)
            results = cursor.execute(query, tuple(queryData)).fetchall()
            if len(results) == 1:
                self.regMark = results[0][0]
                self.type = results[0][1]
                self.isStandardLegal = results[0][2]
                self.isExpandedLegal = results[0][3]
                conn.close()
                return
        self.apiLookup()
        query = "INSERT INTO cards (name, setCode, collNo, regMark, type, isStandardLegal, isExpandedLegal) VALUES (?, ?, ?, ?, ?, ?, ?)"
        cursor.execute(query, (self.name, self.set, self.collNo, self.regMark, self.type, self.isStandardLegal, self.isExpandedLegal))
        conn.commit()
        conn.close()

    def apiLookup(self):
        #construct search query
        search = ''
        if self.name:
            search += f'!name:"{self.name}"'
        if self.set:
            setIDs = {"PR-SV": "svp", "SVI": "sv1", "PAL": "sv2"}
            if self.set in setIDs:
                search += f' set.id:"{setIDs[self.set]}"'
            else:
                search += f' set.ptcgoCode:"{self.set}"'
        if self.collNo:
            search += f' number:*{self.collNo.lstrip("0")}'
        search = search.strip()
        #query the database
        cards = Card.where(q=search, orderBy='-set.releaseDate')
        #see if we have one result
        all3 = False
        nameCheck = False
        while len(cards) != 1:
            if len(cards) > 1:
                logging.warning(f"{search} returned multiple cards, using first result")
                break
            else:
                logging.info(f"no cards returned by {search}")
                if self.name and self.set and self.collNo and not all3:
                    all3 = True
                    #try again with just set and collector number
                    search = search[search.find("set."):]
                elif self.name and (self.set or self.collNo) and not nameCheck:
                    nameCheck = True
                    search = f'!name:"{self.name}"'
                else:
                    break
            cards = Card.where(q=search, orderBy="-set.releaseDate")
        #this is the result, if it's still empty we get an error
        card = cards[0]
        if nameCheck and card.supertype == "Pokémon":
            logging.warning(f"{search} returned a pokemon")
        #populate blank variables with query result
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