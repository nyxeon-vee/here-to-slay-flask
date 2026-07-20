"""
effects.py — the semantic card-effect verbs + the event log.

Cards call these instead of hand-rolling remove_from_party() + discard_pile
so the game can tell a STEAL from a DESTROY from a SACRIFICE. That distinction
is what lets protection effects (Calming Voice) hook one verb without touching
the others — and every effect lands in the event log for free.

Mixed into Game (see game.py); all state lives in Game.__init__, this module
only defines methods.
"""
from __future__ import annotations
import random
from typing import TYPE_CHECKING, cast
from game_logic.base import GameEvent, Hero
if TYPE_CHECKING:
    from game_logic.base import Card
    from game_logic.game import Game
    from game_logic.player import Player

# The log is capped so a long game doesn't grow the payload forever.
LOG_LIMIT = 50


class EffectsMixin:
    if TYPE_CHECKING:  # attributes owned by Game.__init__
        players: list[Player]
        deck: list[Card]
        discard_pile: list[Card]
        event_log: list[dict]

    # ── Event log ────────────────────────────────────────────────────────────

    def log_event(self, text: str, kind: str = "info") -> None:
        """Append one line to the public event log (the in-game 'chat').

        kind steers the UI color: "info" (default), "turn", "combat", "good".
        """
        self.event_log.append({"text": text, "kind": kind})
        del self.event_log[:-LOG_LIMIT]

    # ── Rules verbs ──────────────────────────────────────────────────────────
    # DESTROY / SACRIFICE move a hero to the discard pile (same mechanics,
    # different rules meaning — cards and protections care which one it was).
    # STEAL moves a hero between parties and never touches the discard pile.
    # Callers are responsible for guarding steal_protected BEFORE prompting;
    # see TipsyTootie for the re-prompt pattern.

    @property
    def _game(self) -> Game:
        # The mixin is only ever instantiated as part of Game; this cast lets us
        # pass `self` to card APIs that are typed against the full Game.
        return cast("Game", self)

    def destroy_hero(self, owner: Player, hero: Hero) -> None:
        # The equipped item gets a chance to intercept (Decoy Doll takes the
        # hit instead) — a truthy on_event return cancels the destruction.
        if hero.item is not None and hero.item.on_event(GameEvent.HERO_DESTROYED, self._game, owner):
            return
        owner.remove_from_party(hero)
        item = hero.remove_item()
        if item:
            self.discard_pile.append(item) # add to discard pile the item from the hero too
        self.discard_pile.append(hero)
        self.log_event(f"{owner.name}'s {hero.name} was destroyed", "combat")

    def sacrifice_hero(self, owner: Player, hero: Hero) -> None:
        if hero.item is not None and hero.item.on_event(GameEvent.HERO_SACRIFICED, self._game, owner):
            return
        owner.remove_from_party(hero)
        item = hero.remove_item()
        if item:
            self.discard_pile.append(item) # add to discard pile the item from the hero too
        self.discard_pile.append(hero)
        self.log_event(f"{owner.name} sacrificed {hero.name}", "combat")

    def steal_hero(self, thief: Player, owner: Player, hero: Hero) -> None:
        owner.remove_from_party(hero)
        thief.add_to_party(hero)
        self.log_event(f"{thief.name} stole {hero.name} from {owner.name}", "combat")

    # ── Drawing (deck-safe) ──────────────────────────────────────────────────
    # Official rule: when the draw pile runs out, shuffle the discard pile into
    # a new deck. Cards should draw via these instead of player.draw(game.deck)
    # so an empty deck can never crash an ability mid-generator.

    def _refill_deck_if_empty(self) -> bool:
        """Recycle the discard pile into the deck if needed. Returns True if at
        least one card is drawable afterwards."""
        if self.deck:
            return True
        if not self.discard_pile:
            return False  # both piles empty — nothing anyone can do
        self.deck = self.discard_pile
        self.discard_pile = []
        random.shuffle(self.deck)
        self.log_event("Deck ran out — the discard pile was shuffled into a new deck")
        return True

    def draw_cards(self, player: Player, count: int = 1) -> int:
        """Draw up to `count` cards for `player`, recycling the discard pile as
        needed. Returns how many cards were actually drawn."""
        drawn = 0
        for _ in range(count):
            if not self._refill_deck_if_empty():
                self.log_event("No cards left to draw!")
                break
            player.draw(self.deck)
            drawn += 1
        return drawn

    # ── Target availability guards ───────────────────────────────────────────
    # Used by abilities BEFORE yielding a prompt, so a prompt with zero valid
    # targets (everyone protected / no heroes) fizzles instead of softlocking.

    def has_destroyable_opponent_heroes(self, attacker: Player) -> bool:
        return any(
            any(isinstance(c, Hero) for c in p.party)
            for p in self.players if p is not attacker and not p.destroy_protected
        )

    def has_stealable_opponent_heroes(self, thief: Player) -> bool:
        return any(
            any(isinstance(c, Hero) for c in p.party)
            for p in self.players if p is not thief and not p.steal_protected
        )
