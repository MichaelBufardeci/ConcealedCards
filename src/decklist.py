"""Module that writes pokemon decklists to deck registration sheet"""

from functools import cached_property
import re
import logging
from io import BytesIO
from pathlib import Path
from pypdf import PdfWriter, PdfReader
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from card_info import CardInfo
from exceptions import CardError, DeckError

class Decklist:
    """class representing a pokemon decklist"""

    def __init__(self, *, player_name=None, player_id=None, birthday=None, deck=None):
        self.player_name = None
        self.player_id = None
        self.birthday = {"month": None, "day": None, "year": None }
        self.division = None
        self.deck = []
        self.legality = {"standard": None, "expanded": None}
        error_messages = []
        self.legality = {"standard": None, "expanded": None}
        if player_name:
            self.player_name = str(player_name).strip()
        else:
            #error_messages.append("Player name missing.")
            pass
        if player_id:
            self.player_id = str(player_id).strip()
        else:
            #error_messages.append("Player ID missing.")
            pass
        if birthday:
            birthday = re.split(r"\W", birthday)
            birthday = list(filter(None, birthday))
            self.birthday["month"] = birthday[1].lstrip('0').rjust(2)
            self.birthday["day"] = birthday[2].lstrip('0').rjust(2)
            self.birthday["year"] = birthday [0].lstrip('0').rjust(4)
        else:
            #error_messages.append("Birthday missing.")
            pass
        if deck:
            for line in deck.splitlines():
                line = line.strip()
                if line and line[0].isdigit():
                    line = line.removesuffix(" PH")
                    line = line.split(' ')
                    try:
                        if line[-1][-1].isdigit():
                            card = CardInfo(quantity=line[0], name=' '.join(line[1:-2]),
                                            set_code=line[-2], collector_number=line[-1])
                        else:
                            card = CardInfo(quantity=line[0], name=' '.join(line[1:-1]),
                                            set_code=line[-1])
                        if self.deck and card in self.deck:
                            self.deck[deck.index(card)].quantity += card.quantity
                        else:
                            self.deck.append(card)
                    except CardError as error:
                        error_messages.append(error.message)
            self.deck.sort()
        else:
            error_messages.append("Deck is empty.")
        if error_messages:
            raise DeckError(error_messages)

    def get_legalities(self):
        """determines if deck is standard and/or expanded legal"""
        error_messages = []
        self.legality["standard"] = True
        self.legality["expanded"] = True
        quantity = 0
        for card in self.deck:
            try:
                if card.quantity > 4 and card.set_code != "ENERGY":
                    self.legality["standard"] = False
                    self.legality["expanded"] = False
                    error_messages.append(f"Deck contains {card.quantity} copies of {card.name}"\
                                        f"{card.set_code} {card.collector_number}, maximum is 4.")
                quantity += card.quantity
                if not card.get_standard_legality:
                    self.legality["standard"] = False
                if not card.get_expanded_legality:
                    self.legality["expanded"] = False
                if not (card.get_standard_legality or card.get_expanded_legality):
                    error_messages.append(f"{card.name} {card.set_code} {card.collector_number} is"\
                                          "not legal in standard or expanded.")
            except CardError as error:
                error_messages.append(error.message)
        if quantity != 60:
            self.legality["standard"] = False
            self.legality["expanded"] = False
            error_messages.append(f"Deck contains {quantity} cards, must be 60.")
        if error_messages:
            raise DeckError(error_messages)

    @cached_property
    def get_standard_legality(self):
        """gets this deck's standard legality"""
        if not self.legality["standard"]:
            self.get_legalities()
        return self.legality["standard"]

    @cached_property
    def get_expanded_legality(self):
        """gets this deck's standard legality"""
        if not self.legality["expanded"]:
            self.get_legalities()
        return self.legality["expanded"]

    def write(self):
        """creates a pdf of this decklist"""
        error_messages = []
        #initialize canvas
        packet = BytesIO()
        my_canvas = canvas.Canvas(packet, pagesize=letter)
        my_canvas.setFont("Helvetica", 9)
        # write player info to canvas
        info_y = 722
        if self.player_name:
            my_canvas.drawString(100, info_y, self.player_name)
        if self.player_id:
            my_canvas.drawString(287, info_y, self.player_id)
        if self.birthday["month"] and self.birthday["day"] and self.birthday["year"]:
            # the birthday needs to be split up
            my_canvas.drawString(505, info_y, self.birthday["month"])
            my_canvas.drawString(532, info_y, self.birthday["day"])
            my_canvas.drawString(559, info_y, self.birthday["year"])
            # we still need to check the division box
            division_x = 385
            if int(self.birthday["year"]) >= 2011:
                my_canvas.drawString(division_x, 685, '✓')
            elif int(self.birthday["year"]) <= 2006:
                my_canvas.drawString(division_x, 659, '✓')
            else:
                my_canvas.drawString(division_x, 672, '✓')
        format_y = 740
        if self.get_standard_legality:
            my_canvas.drawString(165, format_y, '✓')
        elif self.get_expanded_legality:
            my_canvas.drawString(205, format_y, '✓')
        else:
            error_messages.append("Deck not standard or expanded legal.")
        #write cards in deck to canvas
        my_canvas.setFontSize(9)
        y_values = {"pokemon_y": 596, "trainer_y": 420, "energy_y": 137.5}
        for card in self.deck:
            supertype = card.get_supertype
            match supertype:
                case "Pokémon":
                    y = y_values["pokemon_y"]
                case "Trainer":
                    y = y_values["trainer_y"]
                case "Energy":
                    y = y_values["energy_y"]
                case _:
                    logging.error("%s %s %s supertype is '%s'", card.get_name, card.get_set_code,
                                card.get_collector_number, supertype)
                    return my_canvas, y_values
            # always write quantity and name
            my_canvas.drawString(280, y, str(card.quantity).rjust(2))
            my_canvas.drawString(305, y, card.get_name)
            # update y for type and write extra info if pokemon
            line_height = 13.1
            match supertype:
                case "Pokémon":
                    my_canvas.drawString(482, y, card.get_set_code)
                    if len(card.get_collector_number) > 3:
                        my_canvas.setFontSize(6)
                    my_canvas.drawString(510, y, card.get_collector_number.rjust(7))
                    my_canvas.setFontSize(9)
                    my_canvas.drawString(560, y, card.get_regulation_mark.rjust(2))
                    y_values["pokemon_y"] -= line_height
                case "Trainer":
                    y_values["trainer_y"] -= line_height
                case "Energy":
                    y_values["energy_y"] -= line_height
        if error_messages:
            raise DeckError(error_messages)
        my_canvas.save()
        #move to the beginning of the StringIO buffer
        packet.seek(0)
        #create a new PDF with Reportlab
        new_pdf = PdfReader(packet)
        #read existing PDF
        with open(Path(__file__).parents[1].resolve() / "res" / "blank.pdf", "rb") as blank_pdf:
            existing_pdf = PdfReader(blank_pdf)
            output = PdfWriter()
            #add the "watermark" (which is the new pdf) on the existing page
            page = existing_pdf.pages[0]
            page.merge_page(new_pdf.pages[0])
            output.add_page(page)
            #finally, write "output" to a temp file
            with BytesIO() as decklist_file:
                output.write(decklist_file)
                return decklist_file.getvalue()
