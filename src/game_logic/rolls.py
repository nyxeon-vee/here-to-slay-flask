"""
rolls.py — dice, modifier windows, and roll resolution, mixed into Game.

Every roll (hero ability, monster attack, challenge) parks the game in
ROLL_PENDING so opponents can play Modifier cards; the socket layer times the
window and calls finish_pending_roll() (or the challenge steps) when it closes.

All state lives in Game.__init__; this module only defines methods.
"""
from __future__ import annotations
import random
from typing import TYPE_CHECKING, cast
from game_logic.base import GameEvent, Hero, Modifier, Monster, Phase, RollOutcome
from game_logic.exceptions import (
    CardNotInHandError,
    InvalidPhaseError,
    PartyNotFulfillRequiermentError,
)
if TYPE_CHECKING:
    from game_logic.base import Card
    from game_logic.game import Game
    from game_logic.player import Player


class RollMixin:
    if TYPE_CHECKING:  # attributes/methods owned by Game and its other mixins
        phase: Phase
        current_player: Player | None
        challenge_context: dict | None
        pending_roll_context: dict | None
        discard_pile: list[Card]
        monster_row: list[Monster]
        last_roll_player_id: str | None
        last_roll_initial: int
        last_roll_current: int
        def _spend_ap(self, player: Player, amount: int) -> None: ...
        def _start_generator(self, kind: str, gen, card: Card, player: Player) -> bool: ...
        def _finalize_kind(self, kind: str) -> None: ...
        def refill_monster_row(self) -> None: ...
        def log_event(self, text: str, kind: str = "info") -> None: ...

    @property
    def _game(self) -> Game:
        # The mixin is only ever instantiated as part of Game; this cast lets us
        # pass `self` to card APIs that are typed against the full Game.
        return cast("Game", self)

    def roll_dice(self, player: Player) -> None:
        # Two six-sided dice. Result lives on the player (player.current_roll) so
        # that two rolls can coexist during a challenge — see _get_rolling_player.
        dice = random.randint(1, 6) + random.randint(1, 6)
        # roll_bonus (Vibrant Glow): flat bonus on every roll. The dice display
        # keeps the raw dice as "initial"; the bonus shows up as a delta.
        player.current_roll = dice + player.roll_bonus
        self.last_roll_player_id = player.player_id
        self.last_roll_initial = dice
        self.last_roll_current = player.current_roll

    def _fire_roll_event(self, player: Player, event: GameEvent) -> None:
        """Notify the roller's leader AND party cards that a roll happened.

        Passives may bump player.current_roll (The Charismatic Song, Anuran
        Cauldron, ...), so re-sync the overlay total afterwards. Party cards
        previously never received roll events at all — only the leader did —
        which left party-monster roll passives dead.
        """
        if player.party_leader:
            player.party_leader.on_event(event, self._game, player)
        for party_card in player.party:
            party_card.on_event(event, self._game, player)
        self.last_roll_current = player.current_roll

    def _get_rolling_player(self) -> Player | None:
        """Whose roll is a modifier currently allowed to change?

        Normally the active player. But during a challenge BOTH sides roll, so
        the modifier window targets whoever is mid-roll (challenge_context's
        "current_roller"), which may be an opponent — not current_player.
        """
        if self.challenge_context:
            return self.challenge_context.get("current_roller")
        return self.current_player

    def play_modifier(self, player: Player, card: Modifier, choice: int = 0) -> None:
        # Modifiers adjust a roll that just happened (the ROLL_PENDING window).
        # `choice` picks between a +/- option on two-sided modifier cards.
        if self.phase != Phase.ROLL_PENDING:
            raise InvalidPhaseError("Modifiers can only be played during a roll!")
        if card.has_choice and choice not in (0, 1):
            raise ValueError("Must choose option 0 or 1 for this modifier")
        if card not in player.hand:
            raise CardNotInHandError(f"{card!r} is not in {player.name}'s hand")
        rolling_player = self._get_rolling_player()  # may be an opponent, mid-challenge
        if rolling_player:
            rolling_player.current_roll += card.options[choice]
            delta = card.options[choice]
            self.log_event(
                f"{player.name} played {card.name} ({'+' if delta >= 0 else ''}{delta}) "
                f"on {rolling_player.name}'s roll"
            )
        self.discard_pile.append(card)
        player.hand.remove(card)
        # Abyss Queen passive: when SOMEONE ELSE modifies your roll, +1. Skip when
        # you modify your own roll, hence the rolling_player != player guard.
        if rolling_player and rolling_player != player:
            for party_card in rolling_player.party:
                party_card.on_event(GameEvent.MODIFIER_PLAYED, self._game, rolling_player)
        if rolling_player:
            # Sync AFTER passives too, so e.g. Abyss Queen's +1 shows in the overlay.
            self.last_roll_current = rolling_player.current_roll

    def attack_monster(self, player: Player, monster: Monster) -> None:
        # Costs 2 AP and a roll. Three outcomes (see Monster.evaluate_roll):
        #   WIN  -> monster joins your party, row refills
        #   LOSE -> monster's failure penalty fires (usually sacrifice a hero)
        #   DRAW -> nothing happens, monster stays in the row
        if not monster.party_requirement.check(player.party, player.party_leader):
            raise PartyNotFulfillRequiermentError("Your party does not meet this monster's requirements!")
        if self.phase != Phase.ACTION:
            raise InvalidPhaseError("Can only attack a monster during action phase!")
        if player != self.current_player:
            raise InvalidPhaseError("It is not your turn!")
        if monster not in self.monster_row:
            raise InvalidPhaseError("That monster is not in the monster row!")

        self._spend_ap(player, 2)
        self.log_event(f"{player.name} attacks {monster.name}", "combat")
        self.phase = Phase.ROLL_PENDING
        self.roll_dice(player)
        # Passives: The Divine Arrow leader +1, Anuran Cauldron party monster +1, ...
        self._fire_roll_event(player, GameEvent.MONSTER_ATTACK)
        self.pending_roll_context = {"type": "monster_attack", "monster": monster, "player": player}
        # Phase stays ROLL_PENDING — game_socket opens the modifier window.
        # Resolution happens in finish_pending_roll() when the window closes.

    def finish_pending_roll(self) -> None:
        """Resolve a hero or monster roll after the modifier window has closed.

        Called by game_socket._advance_window when ROLL_PENDING expires with no
        challenge_context. Reads pending_roll_context, runs the appropriate
        resolution, then returns to ACTION (or AWAITING_CHOICE if the effect
        needs more player input).
        """
        ctx = self.pending_roll_context
        if ctx is None:
            raise InvalidPhaseError("No roll in progress")
        self.pending_roll_context = None
        self.last_roll_player_id = None
        self.last_roll_initial = 0
        self.last_roll_current = 0

        t = ctx["type"]
        if t in ("hero_play", "hero_party"):
            hero: Hero = ctx["hero"]
            player: Player = ctx["player"]
            kind = "hero_play" if t == "hero_play" else "party_ability"
            won = hero.evaluate_roll(player.current_roll) == RollOutcome.WIN
            self.log_event(
                f"{player.name} rolled {player.current_roll} — {hero.name}'s ability "
                + ("activates" if won else "fails"),
                "good" if won else "combat")
            # finish_roll returns the generator from use_ability (on a WIN), or
            # None (on a LOSE — ability doesn't run, item passive fires instead).
            gen = hero.finish_roll(self._game, player)
            if self._start_generator(kind, gen, hero, player):
                return  # generator paused for player input
            self._finalize_kind(kind)

        elif t == "monster_attack":
            monster: Monster = ctx["monster"]
            player: Player = ctx["player"]
            outcome: RollOutcome = monster.evaluate_roll(player.current_roll)
            if outcome == RollOutcome.WIN:
                self.log_event(f"{player.name} rolled {player.current_roll} and slayed {monster.name}!", "good")
                self.monster_row.remove(monster)
                player.add_to_party(monster)
                self.refill_monster_row()
            elif outcome == RollOutcome.LOSE:
                self.log_event(f"{player.name} rolled {player.current_roll} and failed against {monster.name}", "combat")
                gen = monster.apply_failure(self._game, player)
                if self._start_generator("monster_failure", gen, monster, player):
                    return  # generator paused for player input
            else:  # DRAW — nothing happens
                self.log_event(f"{player.name} rolled {player.current_roll} against {monster.name} — nothing happens")
            self.phase = Phase.ACTION
