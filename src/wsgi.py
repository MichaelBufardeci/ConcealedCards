"""module that hosts the website"""

from pathlib import Path
from io import BytesIO
from flask import Flask, render_template, request, send_file
from decklist import create_decklist

app = Flask(__name__)


@app.route('/favicon.ico')
def favicon():
    """reroutes the favicon to /favicon.ico"""

    favicon_path = Path(__file__).parent.resolve() / 'static' / 'favicons' / 'favicon.ico'
    return send_file(favicon_path, mimetype='image/vnd.microsoft.icon')


@app.route('/')
def render_site():
    """renders the homepage"""

    title = "Concealed Cards"
    if app.debug:
        title += " β"
    description = "Concealed Cards fills out Pokémon TCG deck registrion sheets "\
                  "so you don't have to."
    favicon_alt = "A simplified graphic of a water energy in front of two face-down cards."
    return render_template(
        'site.html',
        title=title,
        description=description,
        faviconAlt=favicon_alt
    )


@app.route('/generate_decklist', methods=['POST'])
def generate_decklist():
    """generates a decklist with the user's input"""

    decklist_data = create_decklist(
        request.form['playerName'],
        request.form['playerId'],
        request.form['playerBirthday'],
        request.form['decklist']
    )
    decklist_file = BytesIO(decklist_data)
    return send_file(
        decklist_file,
        mimetype='application/pdf',
        download_name='Deck Registration Sheet.pdf'
    )


if __name__ == "__main__":
    app.run(debug=True)
