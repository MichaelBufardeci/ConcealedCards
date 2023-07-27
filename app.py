from io import BytesIO
from flask import Flask, render_template, request, send_file
from .decklist import createDecklist

app = Flask(__name__)

@app.route("/")
def render_site():
    return render_template("site.html")

@app.route("/generate_decklist", methods=['POST'])
def generate_decklist():
    decklistData = createDecklist(request.form["playerName"], request.form["playerId"], request.form["playerBirthday"], request.form["decklist"])
    decklistFile = BytesIO(decklistData) 
    return send_file(decklistFile, mimetype = "application/pdf", download_name = "Deck Registration Sheet.pdf")