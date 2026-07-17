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
from typing import TYPE_CHECKING
from game_logic.base import Hero
if TYPE_CHECKING:
    from game_logic.base import Card
    from game_logic.player import Player

# The log is capped so a long game doesn't grow the payload forever.
LOG_LIMIT = 50


class EffectsMixin:
    if TYPE_CHECKING:  # attributes owned by Game.__init__
        players: list[Player]
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

    def destroy_hero(self, owner: Player, hero: Hero) -> None:
        owner.remove_from_party(hero)
        self.discard_pile.append(hero)
        self.log_event(f"{owner.name}'s {hero.name} was destroyed", "combat")

    def sacrifice_hero(self, owner: Player, hero: Hero) -> None:
        owner.remove_from_party(hero)
        self.discard_pile.append(hero)
        self.log_event(f"{owner.name} sacrificed {hero.name}", "combat")

    def steal_hero(self, thief: Player, owner: Player, hero: Hero) -> None:
        owner.remove_from_party(hero)
        thief.add_to_party(hero)
        self.log_event(f"{thief.name} stole {hero.name} from {owner.name}", "combat")

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
