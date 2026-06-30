"""
Player: one participant's private state (hand, party, leader, AP).

Deliberately a dumb data holder — it knows how to move its own cards around but
enforces no game rules (whose turn it is, phase checks, AP costs). All of that
lives in Game, so the rules sit in exactly one place.
"""
from __future__ import annotations
from typing import TYPE_CHECKING
from game_logic.exceptions import CardNotInHandError, CardNotInPartyError
if TYPE_CHECKING:
    from game_logic.base import Card, Hero, Leader, Monster

class Player:
    def __init__(self, player_id: str, name: str) -> None:
        self.player_id = player_id
        self.name = name
        self.hand: list[Card] = []                  # cards you can play
        self.party: list[Hero | Monster] = []       # heroes (and slain monsters) in play
        self.party_leader: Leader | None = None     # your permanent leader + its passive
        self.action_points: int = 0                 # spendable this turn (reset to 3 each turn)
        # Result of this player's most recent roll. Stored per-player (not on the
        # Game) so a challenge's two simultaneous rolls don't clobber each other.
        self.current_roll: int = 0

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
