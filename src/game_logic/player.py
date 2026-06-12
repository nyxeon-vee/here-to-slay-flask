from __future__ import annotations
from typing import TYPE_CHECKING
from exceptions import CardNotInHandError, CardNotInPartyError
if TYPE_CHECKING:
    from game_logic.base import Card, Hero, Leader, Monster

class Player:
    def __init__(self, player_id: str, name: str) -> None:
        self.player_id = player_id
        self.name = name
        self.hand: list[Card] = []
        self.party: list[Hero | Monster] = []
        self.party_leader: Leader | None = None
        self.action_points: int = 0 
    def draw(self, deck: list[Card]) -> None:
        self.hand.append(deck.pop())

    def discard(self, card: Card) -> None:
        if card not in self.hand:
            raise CardNotInHandError(f"{card!r} is not in {self.name}'s hand")
        self.hand.remove(card)
    
    def discard_hand(self) -> list[Card]:
        discarded = self.hand.copy()
        self.hand.clear()
        return discarded  
    
    def add_to_party(self, card: Monster | Hero) -> None:
        self.party.append(card)
    
    def remove_from_party(self, card: Hero) -> None:
        if card not in self.party:
            raise CardNotInPartyError
        self.party.remove(card)
