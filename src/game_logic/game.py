from typing import *
from abc import ABC
from player import Player
from exceptions import CardNotInPartyError
from base import Card, Leader, Hero, Monster, RollOutcome
import random


class Game():
    def __init__(self) -> None:
        self.players:List[Player] = []
        self.deck: List[Card] = []
        self.discard_pile: List[Card] = []
        self.leader_deck: List[Leader] = []
        self.current_roll = 0
        self.current_player: Player | None = None
        pass

    def add_player(self, player: Player) -> None:
        self.players.append(player)

    def roll_dice(self) -> None:
        self.current_roll = random.randint(1,6) + random.randint(1,6)
    
    def play_card(self, player: Player, card: Card,
                target_player: Player | None = None,
                target_hero: Hero | None = None,
                choice: int | None = None) -> None:
        player.action_points -= 1
        self.target_player = target_player
        self.target_hero = target_hero
        self.choice = choice
        self._execute_card(player, card)
        self.target_player = None
        self.target_hero = None
        self.choice = None

    def _execute_card(self, player: Player, card: Card) -> None:
        card.apply(self, player)
    
    def attack_moster(self, player: Player, monster: Monster) -> None:
        player.action_points -= 2
        self.roll_dice()
        outcome: RollOutcome = monster.evaluate_roll(self.current_roll)
        if outcome == RollOutcome.WIN:
            player.add_to_party(monster)
            pass
        elif outcome == RollOutcome.LOSE:
            #player.remove_from_party(hero)
            pass
        elif outcome == RollOutcome.DRAW:
            pass

    def use_party_ability(self, player: Player, card: Hero | Monster) -> None:
        if card not in player.party:
            raise CardNotInPartyError
        player.action_points -= 1
        card.use_ability(self, player)