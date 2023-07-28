import os
from io import BytesIO
from flask import Flask, render_template, request, send_file, send_from_directory
from .decklist import createDecklist

app = Flask(__name__)

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route("/")
def render_site():
    return render_template("site.html")

@app.route("/generate_decklist", methods=['POST'])
def generate_decklist():
    decklistData = createDecklist(request.form["playerName"], request.form["playerId"], request.form["playerBirthday"], request.form["decklist"])
    decklistFile = BytesIO(decklistData) 
    return send_file(decklistFile, mimetype = "application/pdf", download_name = "Deck Registration Sheet.pdf")