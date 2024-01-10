"""errors for concealed cards"""

class CardError(Exception):
    """error with a card"""
    message = None

    def __init__(self, message):
        self.message = message

class DeckError(Exception):
    """error with the deck"""
    messages = []

    def __init__(self, messages):
        self.messages = []
        for message in messages:
            self.messages.append(message)
