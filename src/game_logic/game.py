"""
Game: the rules engine and single source of truth for one match.

It owns the decks, the players, and `phase` (a Phase enum that gates every
action). Public methods are the "moves" the Flask/SocketIO layer calls; they
validate against `phase` and the current player, mutate state, and raise on
illegal input. The engine has no knowledge of the network or the UI.

Card abilities that need player input mid-effect are GENERATORS: they
`yield ChoiceType.X` to pause, the engine collects the answer and resumes them
with gen.send(answer). See Hero.use_ability in base.py for the authoring guide
and choices.py for the driving machinery.

The class is split by concern into mixins — one rule keeps that sane:
ALL state is declared here in Game.__init__; mixins only define methods.

    challenge.py — ChallengeMixin: the three-step challenge flow
    rolls.py     — RollMixin:      dice, modifiers, roll resolution
    choices.py   — ChoiceMixin:    generator driving (yield/send/answers)
    effects.py   — EffectsMixin:   destroy/sacrifice/steal verbs + event log
"""
from typing import List
from types import GeneratorType
import random

from game_logic.player import Player
from game_logic.exceptions import (
    CardNotInPartyError,
    InvalidPhaseError,
    PlayerNotEnoughActionPointsError,
    CardNotInHandError,
)
from game_logic.base import Card, Leader, Hero, Magic, Monster, ChoiceType, GameEvent, Phase
from game_logic.challenge import ChallengeMixin
from game_logic.rolls import RollMixin
from game_logic.choices import ChoiceMixin
from game_logic.effects import EffectsMixin


class Game(ChallengeMixin, RollMixin, ChoiceMixin, EffectsMixin):
    def __init__(self) -> None:
        # ── Table state: the cards and players in the match ──────────────────
        self.players: List[Player] = []
        self.deck: List[Card] = []
        self.discard_pile: List[Card] = []
        self.leader_deck: List[Leader] = []
        self.monster_deck: List[Monster] = []
        self.monster_row: list[Monster] = []

        # ── Turn state ───────────────────────────────────────────────────────
        self.phase: Phase = Phase.LOBBY        # what the game is waiting for
        self.current_player: Player | None = None

        # ── "Card on the table" state: a card played but not yet resolved, ───
        #    held here during the CHALLENGE_WINDOW so it can be challenged.
        self.pending_card: Card | None = None
        self.pending_player: Player | None = None
        self.challenge_context: dict | None = None  # set while a challenge is rolling

        # ── Choice scratchpad: filled by the UI, read by _get_choice_answer ──
        #    while phase == AWAITING_CHOICE. pending_choice says which prompt is
        #    open; the rest hold the raw answer (see ChoiceType in base.py).
        self.pending_choice: ChoiceType | None = None
        self.pending_choice_player: Player | None = None  # WHO must answer (often not current_player)
        self.target_card: Card | None = None
        self.target_player: Player | None = None
        self.target_hero: Hero | None = None
        self.choice: int | None = None                    # yes/no or a number
        self.pending_targets: list[Player] = []           # queue for "each player must..." effects
        self.collected_cards: list[Card] = []             # temporary pool to pick from

        # ── Re-entry bookmark ────────────────────────────────────────────────
        #    When an effect pauses (phase == AWAITING_CHOICE) this records the
        #    suspended generator to resume once the answer arrives, plus the
        #    card/player for the UI: {"kind", "gen", "card", "player"}.
        self.paused: dict | None = None

        # ── Roll context: set when ROLL_PENDING, cleared when roll resolves ──
        #    Carries enough info to finish the roll after the modifier window.
        self.pending_roll_context: dict | None = None
        self.last_roll_player_id: str | None = None   # for the roll overlay
        self.last_roll_initial: int = 0               # dice total BEFORE modifiers
        self.last_roll_current: int = 0               # live total AFTER modifiers
        self.message: str | None = None               # message for the choice

        # ── Event log: public play-by-play shown in the UI "chat" panel ──────
        self.event_log: list[dict] = []               # [{"text": ..., "kind": ...}]

    # ── Small shared helpers ────────────────────────────────────────────────

    def _spend_ap(self, player: Player, amount: int) -> None:
        # Charge action points for a move, refusing if the player can't afford it.
        if player.action_points < amount:
            raise PlayerNotEnoughActionPointsError
        player.action_points -= amount

    def _execute_card(self, player: Player, card: Card):
        # Thin indirection over card.apply so callers read clearly and we have
        # one spot to hook logging/effects later. Returns apply's result — a
        # generator for generator-style Magic cards, None otherwise.
        return card.apply(self, player)

    def _advance_to_next_player(self) -> None:
        # Rotate to the next seat (wrapping around) and start their turn.
        if self.current_player is None:
            raise InvalidPhaseError("No current player set")
        current_index = self.players.index(self.current_player)
        next_index = (current_index + 1) % len(self.players)
        self.current_player = self.players[next_index]
        self.start_turn(self.current_player)

    # ── Setup ───────────────────────────────────────────────────────────────

    def add_player(self, player: Player) -> None:
        self.players.append(player)

    def start_game(self) -> None:
        # Deal the opening table: a leader + 5 cards per player, 3 monsters in
        # the row, then hand the first turn to seat 0.
        if self.phase != Phase.LOBBY:
            raise InvalidPhaseError("Game has already started!")
        if len(self.players) < 2:
            raise InvalidPhaseError("Need at least 2 players to start!")

        random.shuffle(self.deck)
        random.shuffle(self.monster_deck)
        random.shuffle(self.leader_deck)

        for player in self.players:
            player.party_leader = self.leader_deck.pop()
            for _ in range(5):
                player.draw(self.deck)

        for _ in range(3):
            self.refill_monster_row()

        self.log_event("Game started", "turn")
        self.current_player = self.players[0]
        self.start_turn(self.current_player)

    # ── Playing a card ──────────────────────────────────────────────────────

    def play_card(self, player: Player, card: Card) -> None:
        # Commit the card to the table and OPEN the challenge window. The card is
        # deliberately NOT resolved yet — opponents get a chance to challenge.
        # The socket layer times the window: if it expires with no challenge it
        # calls resolve_pending_card(); a challenge instead calls play_challenge().
        # (The MAGIC_PLAYED leader passive now fires in _on_card_resolved, i.e.
        # only once the card actually resolves — not if it's challenged away.)
        if self.phase != Phase.ACTION:
            raise InvalidPhaseError("Can only play a card during action phase!")
        if player != self.current_player:
            raise InvalidPhaseError("It is not your turn!")
        if card not in player.hand:
            raise CardNotInHandError(f"{card!r} is not in {player.name}'s hand")
        self._spend_ap(player, card.action_cost)
        self.phase = Phase.CHALLENGE_WINDOW
        self.pending_card = card
        self.pending_player = player
        self.log_event(f"{player.name} played {card.name}")

    def resolve_pending_card(self) -> None:
        # Run the pending card's effect. Also called by close_challenge_roll_2
        # when a challenge fails.
        if self.phase != Phase.CHALLENGE_WINDOW:
            raise InvalidPhaseError("")
        assert self.pending_card is not None and self.pending_player is not None  # set by play_card
        card, player = self.pending_card, self.pending_player
        result = self._execute_card(player, card)
        # A generator-style apply (Magic cards that need input) returns its
        # generator un-executed — drive it; if it pauses, submit_choice will
        # finish the job later. Hero.apply instead runs synchronously and parks
        # the game in ROLL_PENDING (returns None).
        if isinstance(result, GeneratorType):
            if self._start_generator("magic_play", result, card, player):
                return
        if self.phase == Phase.ROLL_PENDING:
            # Hero.roll_and_activate parked us here; pending_roll_context already
            # set. _on_card_resolved will be called by finish_pending_roll() once
            # the modifier window closes. pending_card stays set until then.
            return
        self._on_card_resolved()

    def _on_card_resolved(self) -> None:
        # A played card has FULLY resolved (not challenged away, not still paused
        # on a choice). Fire "card played" leader passives at THIS moment — e.g.
        # The Cloaked Sage draws on a resolved Magic. Firing here rather than at
        # play time is the fix for the old bug where the draw happened the instant
        # a magic paused for input, or even if a challenge later cancelled it.
        card, player = self.pending_card, self.pending_player
        if isinstance(card, Magic) and player and player.party_leader:
            player.party_leader.on_event(GameEvent.MAGIC_PLAYED, self, player)
        self._clear_pending_card()

    def _clear_pending_card(self) -> None:
        # Wipe the per-card scratchpad and hand control back to the active player.
        self.pending_card = None
        self.pending_player = None
        self.target_player = None
        self.target_hero = None
        self.choice = None
        self.phase = Phase.ACTION

    def use_party_ability(self, player: Player, card: Hero) -> None:
        # Activate the ability of a hero already in your party (no card played —
        # unlike playing a hero from hand there's no challenge window, but the
        # roll still opens a modifier window).
        if self.phase != Phase.ACTION:
            raise InvalidPhaseError("Can only use party ability during action phase!")
        if player != self.current_player:
            raise InvalidPhaseError("It is not your turn!")
        if card not in player.party:
            raise CardNotInPartyError
        if card.was_used_this_turn:
            raise InvalidPhaseError(f"{card.name}'s ability has already been used this turn!")
        self._spend_ap(player, card.action_cost)
        self.log_event(f"{player.name} uses {card.name}'s ability")
        card.roll_and_activate(self, player, context_type="hero_party")
        # Phase is now ROLL_PENDING; game_socket opens the modifier window.
        # finish_pending_roll() runs the ability generator when it closes.

    # ── Turn actions ────────────────────────────────────────────────────────

    def start_turn(self, player: Player) -> None:
        # Reset for the new active player. Each turn grants a fresh 3 AP and
        # every hero in their party gets their ability back.
        self.phase = Phase.ACTION
        player.action_points = 3
        player.steal_protected = False # Calming Voice lasts "until your next turn"
        player.challenge_protected = False # Same for iron resolve
        player.destroy_protected = False # Same for mighty blade
        player.roll_bonus = 0            # safety net; normally cleared in end_turn
        self.log_event(f"— {player.name}'s turn —", "turn")
        self.last_roll_player_id = None
        self.last_roll_initial = 0
        self.last_roll_current = 0
        for card in player.party:
            if isinstance(card, Hero):
                card.reset_turn()

    def end_turn(self, player: Player) -> None:
        if self.phase != Phase.ACTION:
            raise InvalidPhaseError("Can only end turn during the action phase")
        if player != self.current_player:
            raise InvalidPhaseError("It is not your turn!")
        # Vibrant Glow lasts "until the END of your turn" — expire it here, not
        # at your next start_turn, or it would boost your challenge rolls made
        # during other players' turns.
        player.roll_bonus = 0
        self.phase = Phase.END_TURN
        self._advance_to_next_player()

    def draw_card(self, player: Player) -> None:
        if self.phase != Phase.ACTION:
            raise InvalidPhaseError("Can only draw card during the action phase")
        if player != self.current_player:
            raise InvalidPhaseError("It is not your turn!")
        self._spend_ap(player, 1)
        player.draw(self.deck)
        self.log_event(f"{player.name} drew a card")

    def discard_all_cards(self, player: Player) -> None:
        # The "mulligan" move: pay 3 AP to dump your whole hand and draw 5 fresh.
        if self.phase != Phase.ACTION:
            raise InvalidPhaseError("Can only discard all cards and draw new ones during action phase")
        if player != self.current_player:
            raise InvalidPhaseError("It is not your turn!")
        self._spend_ap(player, 3)
        self.discard_pile.extend(player.discard_hand())
        for _ in range(5):
            player.draw(self.deck)
        self.log_event(f"{player.name} discarded their hand and drew 5 new cards")

    # ── Board upkeep ────────────────────────────────────────────────────────

    def refill_monster_row(self) -> None:
        # Keep the monster row stocked from the monster deck (called at setup and
        # after each monster is slain). No-op if the deck runs out.
        if self.monster_deck:
            self.monster_row.append(self.monster_deck.pop())

    def check_win_condition(self) -> Player | None:
        """Return the winner, or None. Win by either 3 slain monsters or having
        6 distinct hero classes in your party. (Not yet wired into the flow —
        should be checked after a monster is slain and at end of turn.)"""
        for player in self.players:
            monsters_defeated = sum(isinstance(card, Monster) for card in player.party)
            if monsters_defeated >= 3:
                return player

            hero_classes = {card.hero_class for card in player.party if isinstance(card, Hero)}
            if len(hero_classes) >= 6:
                return player
        return None
