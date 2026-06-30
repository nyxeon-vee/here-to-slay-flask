"""
Card registry: maps card_id -> card class so the rest of the app can build any
card by its string id (e.g. when loading a deck list) without importing each
class. A card opts in by decorating its class with @register("its_id").

Note: the decorator only runs when the card's module is imported, so every card
module must be imported somewhere (typically via the cards package __init__)
for it to appear in CARD_REGISTRY.
"""
from game_logic.base import Card

# card_id -> class, e.g. {"bad_axe": BadAxe}. Look up + call to get an instance.
CARD_REGISTRY: dict[str, type[Card]] = {}

def register(card_id: str):
    """Class decorator that records a card under its id and returns it unchanged."""
    def decorator(cls: type[Card]) -> type[Card]:
        CARD_REGISTRY[card_id] = cls
        return cls
    return decorator