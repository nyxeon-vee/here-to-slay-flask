"""
challenge.py — the three-step challenge flow, mixed into Game.

A challenge is two rolls with a modifier window after EACH, so it can't be one
function — we'd have nowhere to pause for modifiers. It's split into three
steps; the socket layer calls them in order as the timed windows expire,
letting players play modifiers in between. challenge_context carries the two
rollers across the steps.

    play_challenge         -> spend the card, kick off step 1
    start_challenge        -> challenger rolls,  [modifier window]
    close_challenge_roll_1 -> challenged rolls,  [modifier window]
    close_challenge_roll_2 -> compare & resolve

All state lives in Game.__init__; this module only defines methods.
"""
from __future__ import annotations
from typing import TYPE_CHECKING
from game_logic.base import Challenge, GameEvent, Phase
from game_logic.exceptions import CardNotInHandError, InvalidPhaseError
if TYPE_CHECKING:
    from game_logic.base import Card
    from game_logic.player import Player


class ChallengeMixin:
    if TYPE_CHECKING:  # attributes/methods owned by Game and its other mixins
        phase: Phase
        current_player: Player | None
        pending_card: Card | None
        pending_player: Player | None
        challenge_context: dict | None
        discard_pile: list[Card]
        last_roll_player_id: str | None
        last_roll_initial: int
        last_roll_current: int
        def roll_dice(self, player: Player) -> None: ...
        def _fire_roll_event(self, player: Player, event: GameEvent) -> None: ...
        def resolve_pending_card(self) -> None: ...
        def log_event(self, text: str, kind: str = "info") -> None: ...

    def play_challenge(self, player: Player, card: Challenge) -> None:
        # An opponent spends a Challenge card to contest the pending card; this
        # kicks off the two-roll challenge sequence (start_challenge = step 1).
        if self.phase != Phase.CHALLENGE_WINDOW:
            raise InvalidPhaseError("Can only challenge during the challenge window!")
        if player == self.current_player:
            raise InvalidPhaseError("You cannot challenge your own action!")
        # Iron Resolve: the pending player's plays can't be challenged this turn.
        # Checked AFTER the phase check so pending_player is guaranteed to be set,
        # and deliberately server-side — the challenger finds out by trying.
        if self.pending_player and self.pending_player.challenge_protected:
            raise InvalidPhaseError(f"{self.pending_player.name} is protected from Challenges!")
        if card not in player.hand:
            raise CardNotInHandError(f"{card!r} is not in {player.name}'s hand")
        player.hand.remove(card)
        self.discard_pile.append(card)
        pc = self.pending_card
        self.log_event(f"{player.name} challenged {pc.name if pc else 'the card'}!", "combat")
        self.start_challenge(challenger=player)

    def start_challenge(self, challenger: Player) -> None:
        """Step 1: challenger rolls, then open their modifier window."""
        self.challenge_context = {
            "challenger": challenger,
            "challenged": self.pending_player,   # the player whose card is being challenged
            "challenger_roll": None,
        }
        self.challenge_context["current_roller"] = challenger  # steers _get_rolling_player
        self.roll_dice(challenger)
        self._fire_roll_event(challenger, GameEvent.CHALLENGE_ROLL)
        self.phase = Phase.ROLL_PENDING  # modifier window for challenger's roll

    def close_challenge_roll_1(self) -> None:
        """Step 2: challenged player rolls, then open their modifier window."""
        if self.challenge_context is None:
            raise InvalidPhaseError("No challenge in progress")
        ctx = self.challenge_context
        # Lock in the challenger's final roll before moving to the challenged player.
        ctx["challenger_roll"] = ctx["challenger"].current_roll
        challenged = ctx["challenged"]
        ctx["current_roller"] = challenged  # modifiers now target the challenged player
        self.roll_dice(challenged)
        self._fire_roll_event(challenged, GameEvent.CHALLENGE_ROLL)
        self.phase = Phase.ROLL_PENDING  # modifier window for challenged's roll

    def close_challenge_roll_2(self) -> None:
        """Step 3: compare the two rolls and resolve the challenge."""
        if self.challenge_context is None:
            raise InvalidPhaseError("No challenge in progress")
        ctx = self.challenge_context
        challenger: Player = ctx["challenger"]
        challenged: Player = ctx["challenged"]
        self.challenge_context = None

        self.last_roll_player_id = None
        self.last_roll_initial = 0
        self.last_roll_current = 0
        if challenger.current_roll >= challenged.current_roll:  # tie goes to challenger
            # Challenge succeeds: the card is cancelled. It was committed to the
            # table but never resolved, so it's still in the player's hand — pull
            # it out and discard it, then dock the player an action point.
            assert self.pending_card is not None  # invariant: set while a challenge runs
            self.log_event(
                f"Challenge succeeded ({challenger.current_roll} vs {challenged.current_roll}) "
                f"— {self.pending_card.name} is discarded", "combat")
            if self.pending_card in challenged.hand:
                challenged.hand.remove(self.pending_card)
            self.discard_pile.append(self.pending_card)
            self.pending_card = None
            challenged.action_points = max(0, challenged.action_points - 1)
            self.phase = Phase.ACTION
        else:
            # Challenge fails: the card resolves as if never challenged. We came
            # in via ROLL_PENDING, so re-enter the challenge window first —
            # resolve_pending_card insists on it.
            pc = self.pending_card
            self.log_event(
                f"Challenge failed ({challenger.current_roll} vs {challenged.current_roll}) "
                f"— {pc.name if pc else 'the card'} resolves", "good")
            self.phase = Phase.CHALLENGE_WINDOW
            self.resolve_pending_card()
