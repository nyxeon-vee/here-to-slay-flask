from __future__ import annotations
from typing import TYPE_CHECKING, NamedTuple
if TYPE_CHECKING:
    from game_logic.game import Game
    from game_logic.player import Player
from abc import ABC, abstractmethod
from enum import Enum

class RollCondition(Enum):
    AT_LEAST = "at_least"
    AT_MOST  = "at_most"

class RollOutcome(Enum):
    WIN  = "win"
    LOSE = "lose"
    DRAW = "draw"

class RollThreshold(NamedTuple):
    value: int
    condition: RollCondition

    def check(self, roll: int) -> bool:
        return roll <= self.value if self.condition == RollCondition.AT_MOST else roll >= self.value

class CardType(Enum):
    HERO      = "hero"
    MONSTER   = "monster"
    ITEM      = "item"
    MAGIC     = "magic"
    MODIFIER  = "modifier"
    CHALLENGE = "challenge"
    LEADER    = "leader"

class HeroClass(Enum):
    FIGHTER = "fighter"
    RANGER  = "ranger"
    WIZARD  = "wizard"
    BARD    = "bard"
    THIEF   = "thief"
    GUARDIAN = "guardian"

class Card(ABC):
    card_type: CardType
    def __init__(self, card_id: str, name: str, description: str) -> None:
        self.card_id = card_id
        self.name = name
        self.description = description
        super().__init__()

    @abstractmethod
    def apply(self, game: Game, player: Player) -> None:
        """
        Logic on what card does when It is applied..
        """
    
    def to_dict(self) -> dict:
        return {
            "card_id":     self.card_id,
            "name":        self.name,
            "description": self.description,
            "card_type":   self.card_type.value,
        }

    def __repr__(self):
        return f"<{self.__class__.__name__} id={self.card_id!r}>"
    
class Hero(Card):
    card_type: CardType = CardType.HERO

    def __init__(self, card_id, name, description, hero_class: HeroClass, activation_roll: RollThreshold):
        super().__init__(card_id, name, description)
        self.hero_class = hero_class
        self.activation_roll = activation_roll


    def evaluate_roll(self, roll: int) -> RollOutcome:
        return RollOutcome.WIN if self.activation_roll.check(roll) else RollOutcome.LOSE

    def to_dict(self):
        return {
            **super().to_dict(),
            "hero_class":      self.hero_class.value,
            "activation_roll": {"value": self.activation_roll.value, "condition": self.activation_roll.condition.value},
        }
    
class Monster(Card):
    card_type: CardType = CardType.MONSTER

    def __init__(self, card_id: str, name: str, description: str, defeat: RollThreshold, fail: RollThreshold) -> None:
        super().__init__(card_id, name, description)
        self.defeat = defeat
        self.fail   = fail

    def evaluate_roll(self, roll: int) -> RollOutcome:
        if self.defeat.check(roll):
            return RollOutcome.WIN
        if self.fail.check(roll):
            return RollOutcome.LOSE
        return RollOutcome.DRAW

    def to_dict(self):
        return {
            **super().to_dict(),
            "defeat": {"value": self.defeat.value, "condition": self.defeat.condition.value},
            "fail":   {"value": self.fail.value,   "condition": self.fail.condition.value},
        }