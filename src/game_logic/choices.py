"""
choices.py — the generator-driving machinery for card abilities, mixed into Game.

Abilities are generator functions: `yield ChoiceType.X` suspends the ability
until the player answers. This module starts generators, translates the UI's
scratchpad answer into the typed value the generator receives, and resumes it
via gen.send(). See Hero.use_ability in base.py for the authoring guide.

All state lives in Game.__init__; this module only defines methods.
"""
from __future__ import annotations
from typing import TYPE_CHECKING
from game_logic.base import ChoiceType, Phase
from game_logic.exceptions import InvalidPhaseError
if TYPE_CHECKING:
    from game_logic.base import Card, Hero
    from game_logic.player import Player


class ChoiceMixin:
    if TYPE_CHECKING:  # attributes/methods owned by Game and its other mixins
        phase: Phase
        paused: dict | None
        pending_choice: ChoiceType | None
        pending_roll_context: dict | None
        target_card: Card | None
        target_player: Player | None
        target_hero: Hero | None
        choice: int | None
        message: str | None
        def _on_card_resolved(self) -> None: ...

    def _get_choice_answer(self):
        """Extract the typed answer from the scratchpad based on pending_choice.

        For most types the answer is a single object.  For
        CHOOSE_HERO_FROM_OPPONENT_PARTY / CHOOSE_HERO_TO_STEAL the UI sets BOTH
        target_player and target_hero, so we return them as a tuple that the
        generator can unpack with  `target_player, target_hero = yield ...`.
        """
        ct = self.pending_choice
        if ct == ChoiceType.CHOOSE_YES_NO:
            return self.choice == 0           # True = Yes, False = No
        if ct == ChoiceType.CHOOSE_TARGET_PLAYER:
            return self.target_player
        if ct in (ChoiceType.CHOOSE_HERO_FROM_OPPONENT_PARTY, ChoiceType.CHOOSE_HERO_TO_STEAL, ChoiceType.CHOOSE_HERO_TO_DESTROY):
            return (self.target_player, self.target_hero)
        if ct in (ChoiceType.CHOOSE_HERO_FROM_OWN_PARTY, ChoiceType.CHOOSE_HERO_FROM_ANY_PARTY):
            return self.target_hero
        if ct in (ChoiceType.CHOOSE_CARD_FROM_OWN_HAND, ChoiceType.CHOOSE_CARD_FROM_POOL):
            return self.target_card
        if ct == ChoiceType.CHOOSE_CURSED_ITEM_FROM_OWN_PARTY:
            return (self.target_hero, self.target_card)
        if ct == ChoiceType.CHOOSE_NUMBER:
            return self.choice
        return None

    def _start_generator(self, kind: str, gen, card: Card, player: Player) -> bool:
        """Drive a newly-created generator to its first yield.

        `gen` may be None — a plain (no-yield) ability already ran to completion
        when it was called, so there's nothing to drive.

        Returns True if the generator paused (needs player input) — the caller
        should return immediately to let the UI collect the answer.
        Returns False if it finished without pausing — the caller finalizes.
        """
        if gen is None:
            return False
        try:
            choice_type = next(gen)
        except StopIteration:
            return False
        self.pending_choice = choice_type
        self.phase = Phase.AWAITING_CHOICE
        self.paused = {"kind": kind, "gen": gen, "card": card, "player": player}
        return True

    def submit_choice(self) -> None:
        """Resume the paused generator after the UI has filled in the scratchpad.

        Extract the typed answer, clear the scratchpad so the generator gets a
        clean slate, then resume it via gen.send(answer). If the generator
        yields again it needs more input (stay in AWAITING_CHOICE); if it
        raises StopIteration it's done and we finalize the turn.
        """
        if self.phase != Phase.AWAITING_CHOICE or self.paused is None:
            raise InvalidPhaseError("No choice is pending")

        kind, gen = self.paused["kind"], self.paused["gen"]
        answer = self._get_choice_answer()
        # Clear the choice scratchpad — generators keep state in their own local
        # variables and must not see stale values on the next yield.
        self.pending_choice = None
        self.target_card = None
        self.target_player = None
        self.target_hero = None
        self.choice = None
        self.message = None
        try:
            choice_type = gen.send(answer)
            # Generator paused again — record what kind of answer it wants.
            self.pending_choice = choice_type
            self.phase = Phase.AWAITING_CHOICE
            # self.paused stays put — the same generator continues
        except StopIteration:
            self.paused = None
            self._finalize_kind(kind)

    def _finalize_kind(self, kind: str) -> None:
        """Transition to the right phase after a generator finishes.

        If an inner hero triggered a new ROLL_PENDING (e.g. Fuzzy Cheeks
        played another hero via _execute_card), we leave the phase alone —
        finish_pending_roll will call _on_card_resolved when that roll resolves.
        """
        if self.pending_roll_context:
            return  # inner hero roll is in progress; it will finalize later
        if kind in ("hero_play", "magic_play"):
            self._on_card_resolved()
        else:
            self.phase = Phase.ACTION
