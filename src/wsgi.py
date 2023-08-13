from pathlib import Path
from io import BytesIO
from flask import Flask, render_template, request, send_file
from decklist import createDecklist

app = Flask(__name__)

@app.route('/favicon.ico')
def favicon():
    #return send_from_directory(Path.joinPath(Path(__file__).parents[1].resolve(), 'static', 'favicons'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')
    return send_file(Path(__file__).parent.resolve() / 'static' / 'favicons' / 'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/')
def render_site():
    title = "Concealed Cards"
    if app.debug:
        title += " β"
    description = "Concealed Cards fills out Pok&#233;mon TCG deck registrion sheets so you don't have to."
    faviconAlt = "A simplified graphic of a water energy in front of two face-down cards."
    return render_template('site.html', title=title, description=description, faviconAlt=faviconAlt)

@app.route('/generate_decklist', methods=['POST'])
def generate_decklist():
    decklistData = createDecklist(request.form['playerName'], request.form['playerId'], request.form['playerBirthday'], request.form['decklist'])
    decklistFile = BytesIO(decklistData) 
    return send_file(decklistFile, mimetype='application/pdf', download_name='Deck Registration Sheet.pdf')

if __name__ == "__main__":
    app.run(debug=True)