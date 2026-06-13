from typing import List
from player import Player
from exceptions import CardNotInPartyError, InvalidPhaseError, PlayerNotEnoughActionPointsError, CardNotInHandError, PartyNotFulfillRequiermentError
from base import Card, Leader, Hero, Monster, RollOutcome, Modifier, Challenge, ChoiceType
from enum import Enum, auto
import random

class Phase(Enum):
    LOBBY               = auto()
    ACTION              = auto()
    CHALLENGE_WINDOW    = auto()
    ROLL_PENDING        = auto()
    AWAITING_CHOICE     = auto()
    END_TURN            = auto()


class Game():
    def __init__(self) -> None:
        self.players: List[Player] = []
        self.deck: List[Card] = []
        self.discard_pile: List[Card] = []
        self.leader_deck: List[Leader] = []
        self.monster_deck: List[Monster] = []
        self.monster_row: list[Monster] = []
        self.phase: Phase = Phase.LOBBY
        self.current_roll = 0
        self.current_player: Player | None = None
        self.pending_choice: ChoiceType | None = None
        self.pending_card: Card | None = None
        self.pending_player: Player | None = None

    def _spend_ap(self, player: Player, amount: int) -> None:
        if player.action_points < amount:
            raise PlayerNotEnoughActionPointsError
        player.action_points -= amount

    def _execute_card(self, player: Player, card: Card) -> None:
        card.apply(self, player)

    def _advance_to_next_player(self) -> None:
        if self.current_player is None:
            raise InvalidPhaseError("No current player set")
        current_index = self.players.index(self.current_player)
        next_index = (current_index + 1) % len(self.players)
        self.current_player = self.players[next_index]
        self.start_turn(self.current_player)

    def start_game(self) -> None:
        
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

    def roll_dice(self) -> None:
        self.current_roll = random.randint(1, 6) + random.randint(1, 6)

    def play_card(self, player: Player, card: Card,
                target_player: Player | None = None,
                target_hero: Hero | None = None,
                choice: int | None = None) -> None:
        
        if self.phase != Phase.ACTION:
            raise InvalidPhaseError("Can only play a card during action phase!")
        if player != self.current_player:
            raise InvalidPhaseError("It is not your turn!")
        if card not in player.hand:
            raise CardNotInHandError(f"{card!r} is not in {player.name}'s hand")
        
        self._spend_ap(player, card.action_cost)
        self.target_player = target_player
        self.target_hero = target_hero
        self.choice = choice
        self.phase = Phase.CHALLENGE_WINDOW
        self.pending_card = card
        self.pending_player = player
        #await 
        self.resolve_pending_card()
    
    def resolve_pending_card(self) -> None:
        if self.phase != Phase.CHALLENGE_WINDOW:
            raise InvalidPhaseError("")
        self._execute_card(self.pending_player, self.pending_card)
        self.pending_card = None
        self.pending_player = None
        self.target_player = None
        self.target_hero = None
        self.choice = None
        self.phase = Phase.ACTION

    def play_modifier(self, player: Player, card: Modifier) -> None:

        if self.phase != Phase.ROLL_PENDING:
            raise InvalidPhaseError("Modifiers can only be played during a roll!")
        if card not in player.hand:
            raise CardNotInHandError(f"{card!r} is not in {player.name}'s hand")
        
        self.current_roll += card.options[self.choice or 0]
        self.discard_pile.append(card)
        player.hand.remove(card)

    def play_challenge(self, player: Player, card: Challenge) -> None:
        if self.phase != Phase.ACTION:
            raise InvalidPhaseError("Can only challenge during action phase!")
        if player == self.current_player:
            raise InvalidPhaseError("You cannot challenge your own action!")
        if card not in player.hand:
            raise CardNotInHandError(...)
        self._execute_card(player, card)

    def attack_monster(self, player: Player, monster: Monster) -> None:

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
        self.roll_dice()
        outcome: RollOutcome = monster.evaluate_roll(self.current_roll)
        if outcome == RollOutcome.WIN:
            self.monster_row.remove(monster)
            player.add_to_party(monster)
            self.refill_monster_row()
        elif outcome == RollOutcome.LOSE:
            self.phase = Phase.AWAITING_CHOICE
            #The moster has code that decides what happens when you lose
            return
        self.phase = Phase.ACTION

    def use_party_ability(self, player: Player, card: Hero) -> None:
        if self.phase != Phase.ACTION:
            raise InvalidPhaseError("Can only use party ability during action phase!")
        if player != self.current_player:
            raise InvalidPhaseError("It is not your turn!")
        if card not in player.party:
            raise CardNotInPartyError
        self._spend_ap(player, card.action_cost)
        card.use_ability(self, player)

    def discard_all_cards(self, player: Player) -> None:
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
        self.monster_row.append(self.monster_deck.pop())

    def check_win_condition(self) -> Player | None:
        for player in self.players:
            monsters_defeated = sum(isinstance(card, Monster) for card in player.party)
            if monsters_defeated >= 3:
                return player

            hero_classes = {card.hero_class for card in player.party if isinstance(card, Hero)}
            if len(hero_classes) >= 6:
                return player
        return None
