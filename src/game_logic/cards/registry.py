from base import Card

CARD_REGISTRY: dict[str, type[Card]] = {}

def register(card_id: str):
    def decorator(cls: type[Card]) -> type[Card]:
        CARD_REGISTRY[card_id] = cls
        return cls
    return decorator