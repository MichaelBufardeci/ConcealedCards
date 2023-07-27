import re
import logging
from .cardInfo import cardInfo
from io import BytesIO
from os import path
from pypdf import PdfWriter, PdfReader
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from pokemontcgsdk import RestClient

_canvas = None
_pokemonY = None
_trainerY = None
_energyY = None


def writeCard(cardInfo):
    global _canvas, _pokemonY, _trainerY, _energyY
    #jump to line
    type = cardInfo.getType()
    match type:
        case "Pokémon":
            y = _pokemonY
        case "Trainer":
            y = _trainerY
        case "Energy":
            y = _energyY
    #always write quantity and name
    _canvas.drawString(275, y, str(cardInfo.getQuantity()).rjust(2))
    _canvas.drawString(299, y, cardInfo.getName())
    #update y for type and write extra info if pokemon
    lineHeight = 11.5
    match type:
        case "Pokémon":
            _canvas.drawString(449, y, cardInfo.getSet())
            if len(cardInfo.getCollNo()) > 3:
                _canvas.setFontSize(6)
            _canvas.drawString(479, y, cardInfo.getCollNo().rjust(7))
            _canvas.setFontSize(9)
            _canvas.drawString(520, y, cardInfo.getRegMark().rjust(2))
            _pokemonY -= lineHeight
        case "Trainer":
            _trainerY -= lineHeight
        case "Energy":
            _energyY -= lineHeight
    return

def createDecklist(name = None, id = None, birthday = None, decklist = None):
    global _canvas, _pokemonY, _trainerY, _energyY
    filePath = path.realpath(path.dirname(__file__))
    #get API key
    apiKey = None
    with open(path.join(filePath, "API key.txt")) as reader:
        apiKey = reader.read().strip()
        #connect to API
    if apiKey:
        RestClient.configure(apiKey)
    else:
        logging.warning("API key not found")
    #create canvas for decklist
    packet = BytesIO()
    _canvas = canvas.Canvas(packet, pagesize=letter)
    _canvas.setFont("Helvetica", 9)
    #write player info to canvas
    infoY = 676
    if name:
        _canvas.drawString(120, infoY, name)
    if id:
        _canvas.drawString(284, infoY, id)
    if birthday:
        #the birthday needs to be split up
        birthday = re.split("\W", birthday)
        birthday = list(filter(None, birthday))
        _canvas.drawString(471, infoY, birthday[1].lstrip('0').rjust(2))
        _canvas.drawString(495, infoY, birthday[2].lstrip('0').rjust(2))
        _canvas.drawString(519, infoY, birthday[0])
        #we still need to check the division box
        divisionX = 366.5
        if int(birthday[2]) >= 2011:
            _canvas.drawString(divisionX, 644, '✓')
        elif int(birthday[2]) <= 2006:
            _canvas.drawString(divisionX, 620, '✓')
        else:
            _canvas.drawString(divisionX, 632, '✓')
    #write decklist to canvas
    deck = []
    decklist = decklist.splitlines()
    for line in decklist:
        line = line.strip()
        if line and line[0].isdigit():
            line = line.removesuffix(" PH")
            line = line.split(' ')
            card = cardInfo(quantity = line[0], name = ' '.join(line[1:-2]), set = line[-2], collNo = line[-1])
            if card in deck:
                deck[deck.index(card)].quantity += card.quantity
            else:
                deck.append(card)
    deck.sort()
    _canvas.setFontSize(9)
    #we need to reset these y values for a reason I do not fully understand
    _pokemonY = 565.5
    _trainerY = 411.5
    _energyY = 165.5
    standardLegal = True
    expandedLegal = True
    for card in deck:
        writeCard(card)
        if standardLegal and not card.getStandardLegality():
            standardLegal = False
            print(f"{card.getName()} is not standard legal")
        if expandedLegal and not card.getExpandedLegality():
            expandedLegal = False
            print(f"{card.getName()} is not expanded legal")
    formatY = 691
    if standardLegal:
        _canvas.drawString(175, formatY, '✓')
    elif expandedLegal:
        _canvas.drawString(219, formatY, '✓')
    _canvas.save()
    #move to the beginning of the StringIO buffer
    packet.seek(0)
    # create a new PDF with Reportlab
    new_pdf = PdfReader(packet)
    # read existing PDF
    existing_pdf = PdfReader(open(path.join(filePath, "blank.pdf"), "rb"))
    output = PdfWriter()
    # add the "watermark" (which is the new pdf) on the existing page
    page = existing_pdf.pages[0]
    page.merge_page(new_pdf.pages[0])
    output.add_page(page)
    # finally, write "output" to a temp file
    with BytesIO() as decklistFile:
        output.write(decklistFile)
        return decklistFile.getvalue()