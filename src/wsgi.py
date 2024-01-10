"""module that hosts the website"""

from pathlib import Path
from io import BytesIO
import logging
from flask import Flask, render_template, request, send_file
from decklist import Decklist
from exceptions import DeckError

app = Flask(__name__)

@app.route('/favicon.ico')
def favicon():
    """reroutes the favicon to /favicon.ico"""

    favicon_path = Path(__file__).parent.resolve() / 'static' / 'favicons' / 'favicon.ico'
    return send_file(favicon_path, mimetype='image/vnd.microsoft.icon')

@app.route('/')
def render_site(warnings=None, name=None, player_id=None, birthday=None, decklist=None):
    """renders the homepage"""

    title = "Concealed Cards"
    if app.debug:
        title += " β"
    description = "Concealed Cards fills out Pokémon TCG deck registration sheets so you don't"\
                  "have to."
    favicon_alt = "A simplified graphic of a water energy in front of two face-down cards."
    error_messages = None
    if warnings:
        error_messages = "\r\n".join(warnings)
    if not decklist:
        decklist = ""
    return render_template('site.html', title=title, description=description,
                           favicon_alt=favicon_alt, error_messages=error_messages, name=name,
                           id=player_id, birthday=birthday, decklist=decklist)

@app.route('/generate_decklist', methods=['POST'])
def generate_decklist():
    """generates a decklist with the user's input"""
    player_name = request.form['playerName']
    player_id = request.form['playerId']
    player_birthday = request.form['playerBirthday']
    deck_list = request.form['decklist']
    decklist_data = None
    try:
        decklist_data = Decklist(player_name=player_name,
                            player_id=player_id,
                            birthday=player_birthday,
                            deck=deck_list)
        decklist_file = BytesIO(decklist_data.write())
        return send_file(decklist_file, mimetype='application/pdf',
                         download_name='Deck Registration Sheet.pdf')
    except DeckError as error:
        return render_site(warnings=error.messages, name=player_name, player_id=player_id,
                           birthday=player_birthday, decklist=deck_list)

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    app.run(debug=True)
