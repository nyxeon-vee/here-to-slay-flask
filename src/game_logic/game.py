"""
Game: the rules engine and single source of truth for one match.

It owns the decks, the players, and `phase` (a Phase enum that gates every
action). Public methods are the "moves" the Flask/SocketIO layer calls; they
validate against `phase` and the current player, mutate state, and raise on
illegal input. The engine has no knowledge of the network or the UI.

Because some card effects need player input mid-resolution, an effect can pause
by setting `phase = AWAITING_CHOICE` and returning; the outer layer fills in the
answer and re-calls the effect. The `target_*` / `choice` / `collected_cards`
fields below are the scratchpad that carries state across those re-entries.
"""
from typing import List
from game_logic.player import Player
from game_logic.exceptions import (
    CardNotInPartyError,
    InvalidPhaseError,
    PlayerNotEnoughActionPointsError,
    CardNotInHandError,
    PartyNotFulfillRequiermentError,
)
from game_logic.base import Card, Leader, Hero, Magic, Monster, RollOutcome, Modifier, Challenge, ChoiceType, GameEvent, Phase
import random


class Game():
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

        # ── Choice scratchpad: filled by the UI, read by a paused effect ─────
        #    while phase == AWAITING_CHOICE. pending_choice says which prompt is
        #    open; the rest hold the answer (see ChoiceType in base.py).
        self.pending_choice: ChoiceType | None = None
        self.pending_choice_player: Player | None = None  # WHO must answer (often not current_player)
        self.target_card: Card | None = None
        self.target_player: Player | None = None
        self.target_hero: Hero | None = None
        self.choice: int | None = None                    # yes/no or a number
        self.pending_targets: list[Player] = []           # queue for "each player must..." effects
        self.collected_cards: list[Card] = []             # temporary pool to pick from

    def _spend_ap(self, player: Player, amount: int) -> None:
        # Charge action points for a move, refusing if the player can't afford it.
        if player.action_points < amount:
            raise PlayerNotEnoughActionPointsError
        player.action_points -= amount

    def _execute_card(self, player: Player, card: Card) -> None:
        # Thin indirection over card.apply so callers read clearly and we have
        # one spot to hook logging/effects later.
        card.apply(self, player)

    def _get_rolling_player(self) -> Player | None:
        """Whose roll is a modifier currently allowed to change?

        Normally the active player. But during a challenge BOTH sides roll, so
        the modifier window targets whoever is mid-roll (challenge_context's
        "current_roller"), which may be an opponent — not current_player.
        """
        if self.challenge_context:
            return self.challenge_context.get("current_roller")
        return self.current_player

    def _advance_to_next_player(self) -> None:
        # Rotate to the next seat (wrapping around) and start their turn.
        if self.current_player is None:
            raise InvalidPhaseError("No current player set")
        current_index = self.players.index(self.current_player)
        next_index = (current_index + 1) % len(self.players)
        self.current_player = self.players[next_index]
        self.start_turn(self.current_player)

    # A challenge is two rolls with a modifier window after EACH, so it can't be
    # one function — we'd have nowhere to pause for modifiers. It's split into
    # three steps; the outer layer calls them in order, letting players play
    # modifiers in between. challenge_context carries the two rollers across them.
    #
    #   start_challenge       -> challenger rolls,  [modifier window]
    #   close_challenge_roll_1 -> challenged rolls, [modifier window]
    #   close_challenge_roll_2 -> compare & resolve

    def start_challenge(self, challenger: Player) -> None:
        """Step 1: challenger rolls, then open their modifier window."""
        self.challenge_context = {
            "challenger": challenger,
            "challenged": self.pending_player,   # the player whose card is being challenged
            "challenger_roll": None,
        }
        self.challenge_context["current_roller"] = challenger  # steers _get_rolling_player
        challenger.current_roll = random.randint(1, 6) + random.randint(1, 6)
        if challenger.party_leader:
            challenger.party_leader.on_event(GameEvent.CHALLENGE_ROLL, self, challenger)
        self.phase = Phase.ROLL_PENDING  # modifier window for challenger's roll

    def close_challenge_roll_1(self) -> None:
        """Step 2: challenged player rolls, then open their modifier window."""
        if self.challenge_context is None:
            raise InvalidPhaseError("No challenge in progress")
        ctx = self.challenge_context
        challenged = ctx["challenged"]
        ctx["current_roller"] = challenged  # modifiers now target the challenged player
        challenged.current_roll = random.randint(1, 6) + random.randint(1, 6)
        if challenged.party_leader:
            challenged.party_leader.on_event(GameEvent.CHALLENGE_ROLL, self, challenged)
        self.phase = Phase.ROLL_PENDING  # modifier window for challenged's roll

    def close_challenge_roll_2(self) -> None:
        """Step 3: compare the two rolls and resolve the challenge."""
        if self.challenge_context is None:
            raise InvalidPhaseError("No challenge in progress")
        ctx = self.challenge_context
        challenger: Player = ctx["challenger"]
        challenged: Player = ctx["challenged"]
        self.challenge_context = None

        if challenger.current_roll >= challenged.current_roll:  # tie goes to challenger
            # Challenge succeeds: the played card is cancelled (discarded, never
            # resolved) and the challenged player loses an action point.
            assert self.pending_card is not None  # invariant: set while a challenge runs
            self.discard_pile.append(self.pending_card)
            self.pending_card = None
            challenged.action_points = max(0, challenged.action_points - 1)
            self.phase = Phase.ACTION
        else:
            # Challenge fails: the card goes through as if never challenged.
            self.resolve_pending_card()

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

        self.current_player = self.players[0]
        self.start_turn(self.current_player)

    def add_player(self, player: Player) -> None:
        self.players.append(player)

    def roll_dice(self, player: Player) -> None:
        # Two six-sided dice. Result lives on the player (player.current_roll) so
        # that two rolls can coexist during a challenge — see _get_rolling_player.
        player.current_roll = random.randint(1, 6) + random.randint(1, 6)

    def play_card(self, player: Player, card: Card) -> None:
        # Spend the cost, then move into the challenge window. NOTE: this
        # currently resolves the card immediately; once opponents can actually
        # challenge, the resolve_pending_card() call moves out to the moment the
        # challenge window closes (or a challenge is declined).
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
        self.resolve_pending_card()
        # Leader passive: The Cloaked Sage draws a card whenever you play Magic.
        if isinstance(card, Magic) and player.party_leader:
            player.party_leader.on_event(GameEvent.MAGIC_PLAYED, self, player)

    def resolve_pending_card(self) -> None:
        # Run the pending card's effect and clear the per-card scratchpad.
        # Also called by close_challenge_roll_2 when a challenge fails.
        if self.phase != Phase.CHALLENGE_WINDOW:
            raise InvalidPhaseError("")
        self._execute_card(self.pending_player, self.pending_card)
        self.pending_card = None
        self.pending_player = None
        self.target_player = None
        self.target_hero = None
        self.choice = None
        self.phase = Phase.ACTION

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
        self.discard_pile.append(card)
        player.hand.remove(card)
        # Abyss Queen passive: when SOMEONE ELSE modifies your roll, +1. Skip when
        # you modify your own roll, hence the rolling_player != player guard.
        if rolling_player and rolling_player != player:
            for party_card in rolling_player.party:
                party_card.on_event(GameEvent.MODIFIER_PLAYED, self, rolling_player)

    def play_challenge(self, player: Player, card: Challenge) -> None:
        # An opponent spends a Challenge card to contest the pending card; this
        # kicks off the two-roll challenge sequence (start_challenge = step 1).
        if self.phase != Phase.CHALLENGE_WINDOW:
            raise InvalidPhaseError("Can only challenge during the challenge window!")
        if player == self.current_player:
            raise InvalidPhaseError("You cannot challenge your own action!")
        if card not in player.hand:
            raise CardNotInHandError(f"{card!r} is not in {player.name}'s hand")
        player.hand.remove(card)
        self.discard_pile.append(card)
        self.start_challenge(challenger=player)

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
        self.phase = Phase.ROLL_PENDING
        self.roll_dice(player)
        # Leader passive: The Divine Arrow adds +1 when attacking a monster.
        if player.party_leader:
            player.party_leader.on_event(GameEvent.MONSTER_ATTACK, self, player)
        outcome: RollOutcome = monster.evaluate_roll(player.current_roll)
        if outcome == RollOutcome.WIN:
            self.monster_row.remove(monster)
            player.add_to_party(monster)
            self.refill_monster_row()
        elif outcome == RollOutcome.LOSE:
            # The monster decides the penalty; it may need player input (pick a
            # hero to sacrifice), so it can leave us in AWAITING_CHOICE.
            monster.apply_failure(self, player)
            self.phase = Phase.AWAITING_CHOICE
            return
        self.phase = Phase.ACTION

    def use_party_ability(self, player: Player, card: Hero) -> None:
        # Activate the ability of a hero already in your party (no new roll —
        # unlike playing a hero from hand). Re-entrant, same as Hero.use_ability.
        if self.phase != Phase.ACTION:
            raise InvalidPhaseError("Can only use party ability during action phase!")
        if player != self.current_player:
            raise InvalidPhaseError("It is not your turn!")
        if card not in player.party:
            raise CardNotInPartyError
        self._spend_ap(player, card.action_cost)
        card.use_ability(self, player)

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

    def end_turn(self, player: Player) -> None:
        if self.phase != Phase.ACTION:
            raise InvalidPhaseError("Can only end turn during the action phase")
        if player != self.current_player:
            raise InvalidPhaseError("It is not your turn!")
        self.phase = Phase.END_TURN
        self._advance_to_next_player()

    def start_turn(self, player: Player) -> None:
        # Reset for the new active player. Each turn grants a fresh 3 AP.
        self.phase = Phase.ACTION
        player.action_points = 3

    def draw_card(self, player: Player) -> None:
        if self.phase != Phase.ACTION:
            raise InvalidPhaseError("Can only draw card during the action phase")
        if player != self.current_player:
            raise InvalidPhaseError("It is not your turn!")
        self._spend_ap(player, 1)
        player.draw(self.deck)

    def refill_monster_row(self) -> None:
        # Keep the monster row stocked from the monster deck (called at setup and
        # after each monster is slain).
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
