"""Module that writes pokemon decklists to deck registration sheet"""

import re
import logging
from io import BytesIO
from pathlib import Path
from pypdf import PdfWriter, PdfReader
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from pokemontcgsdk import RestClient
from card_info import CardInfo

def write_player_info(my_canvas, player_name=None, player_id=None, birthday=None):
    """writes player name, ID, birthday, and age division to deck registration sheet"""

    # write player info to canvas
    info_y = 722
    if player_name:
        my_canvas.drawString(100, info_y, player_name)
    if player_id:
        my_canvas.drawString(287, info_y, player_id)
    if birthday:
        # the birthday needs to be split up
        birthday = re.split(r"\W", birthday)
        birthday = list(filter(None, birthday))
        my_canvas.drawString(505, info_y, birthday[1].lstrip('0').rjust(2))
        my_canvas.drawString(532, info_y, birthday[2].lstrip('0').rjust(2))
        my_canvas.drawString(559, info_y, birthday[0])
        # we still need to check the division box
        division_x = 385
        if int(birthday[0]) >= 2011:
            my_canvas.drawString(division_x, 685, '✓')
        elif int(birthday[0]) <= 2006:
            my_canvas.drawString(division_x, 659, '✓')
        else:
            my_canvas.drawString(division_x, 672, '✓')
    return my_canvas

def write_card(my_canvas, card_info, y_values):
    """writes a pokemon card to the deck registration pdf"""

    # jump to line
    supertype = card_info.get_supertype
    match supertype:
        case "Pokémon":
            y = y_values["pokemon_y"]
        case "Trainer":
            y = y_values["trainer_y"]
        case "Energy":
            y = y_values["energy_y"]
        case _:
            logging.error("%s %s %s supertype is '%s'", card_info.get_name, card_info.get_set_code,
                          card_info.get_collector_number, supertype)
            return my_canvas, y_values
    # always write quantity and name
    my_canvas.drawString(280, y, str(card_info.quantity).rjust(2))
    my_canvas.drawString(305, y, card_info.get_name)
    # update y for type and write extra info if pokemon
    line_height = 13.1
    match supertype:
        case "Pokémon":
            my_canvas.drawString(482, y, card_info.get_set_code)
            if len(card_info.get_collector_number) > 3:
                my_canvas.setFontSize(6)
            my_canvas.drawString(510, y, card_info.get_collector_number.rjust(7))
            my_canvas.setFontSize(9)
            my_canvas.drawString(560, y, card_info.get_regulation_mark.rjust(2))
            y_values["pokemon_y"] -= line_height
        case "Trainer":
            y_values["trainer_y"] -= line_height
        case "Energy":
            y_values["energy_y"] -= line_height
    return my_canvas, y_values

def write_decklist(my_canvas, decklist=None):
    """writes pokemon cards to deck registration sheet"""

    deck = []
    decklist = decklist.splitlines()
    for line in decklist:
        line = line.strip()
        if line and line[0].isdigit():
            line = line.removesuffix(" PH")
            line = line.split(' ')
            if line[-1][-1].isdigit():
                card = CardInfo(quantity=line[0], name=' '.join(line[1:-2]), set_code=line[-2],
                                collector_number=line[-1])
            else:
                card = CardInfo(quantity=line[0], name=' '.join(line[1:-1]), set_code=line[-1])
            if card in deck:
                deck[deck.index(card)].quantity += card.quantity
            else:
                deck.append(card)
    deck.sort()
    my_canvas.setFontSize(9)
    y_values = {"pokemon_y": 596, "trainer_y": 420, "energy_y": 137.5}
    standard_legal = True
    expanded_legal = True
    deck_quantity = 0
    for card in deck:
        my_canvas, y_values = write_card(my_canvas, card, y_values)
        deck_quantity += card.quantity
        if standard_legal and not card.get_standard_legality:
            standard_legal = False
        if expanded_legal and not card.get_expanded_legality:
            expanded_legal = False
    if deck_quantity == 60:
        format_y = 740
        if standard_legal:
            my_canvas.drawString(165, format_y, '✓')
        elif expanded_legal:
            my_canvas.drawString(205, format_y, '✓')
    return my_canvas

def create_decklist(player_name=None, player_id=None, birthday=None, decklist=None):
    """fills out a pokemon deck registration sheet pdf"""

    # get API key
    try:
        api_key_path = Path(__file__).parents[1].resolve() / "res" / "APIkey.txt"
        with open(api_key_path, encoding="utf-8") as reader:
            api_key = reader.read().strip()
            # connect to API
            RestClient.configure(api_key)
    except OSError:
        logging.warning("API key not found")
    # create canvas for decklist
    packet = BytesIO()
    my_canvas = canvas.Canvas(packet, pagesize=letter)
    my_canvas.setFont("Helvetica", 9)
    # write canvas
    my_canvas = write_player_info(my_canvas, player_name, player_id, birthday)
    my_canvas = write_decklist(my_canvas, decklist)
    my_canvas.save()
    # move to the beginning of the StringIO buffer
    packet.seek(0)
    # create a new PDF with Reportlab
    new_pdf = PdfReader(packet)
    # read existing PDF
    with open(Path(__file__).parents[1].resolve() / "res" / "blank.pdf", "rb") as blank_pdf:
        existing_pdf = PdfReader(blank_pdf)
        output = PdfWriter()
        # add the "watermark" (which is the new pdf) on the existing page
        page = existing_pdf.pages[0]
        page.merge_page(new_pdf.pages[0])
        output.add_page(page)
        # finally, write "output" to a temp file
        with BytesIO() as decklist_file:
            output.write(decklist_file)
            return decklist_file.getvalue()
