from __future__ import annotations
from typing import TYPE_CHECKING, NamedTuple
if TYPE_CHECKING:
    from game_logic.game import Game
    from game_logic.player import Player
from abc import ABC, abstractmethod
from enum import Enum, auto

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

class ChoiceType(Enum):
    SACRIFICE_ANY_HERO       = auto()
    SACRIFICE_HERO_OF_CLASS  = auto()
    RETURN_HERO_TO_HAND      = auto()
    CHOOSE_TARGET_PLAYER     = auto()
    CHOOSE_HERO_FROM_PARTY   = auto()

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

class PartyRequirement(NamedTuple):
    min_heroes: int
    required_classes: tuple[HeroClass, ...]

    def check(self, party: list, leader: Leader) -> bool:
        hero_count = sum(isinstance(c, Hero) for c in party)
        if hero_count < self.min_heroes:
            return False
        party_classes = {c.hero_class for c in party if isinstance(c, Hero)} | {leader.hero_class}
        return all(cls in party_classes for cls in self.required_classes)
    
class Card(ABC):
    card_type: CardType
    action_cost: int = 1
    def __init__(self, card_id: str, name: str, description: str) -> None:
        self.card_id = card_id
        self.name = name
        self.description = description
        super().__init__()
        
    @abstractmethod
    def apply(self, game: Game, player: Player) -> None: ...


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
        self.item: Item | None = None

    def add_item(self, item: Item) -> None:
        self.item = item

    @abstractmethod
    def use_ability(self, game: Game, player: Player) -> None: ...

    def evaluate_roll(self, roll: int) -> RollOutcome:
        return RollOutcome.WIN if self.activation_roll.check(roll) else RollOutcome.LOSE

    def to_dict(self):
        return {
            **super().to_dict(),
            "hero_class":      self.hero_class.value,
            "activation_roll": {"value": self.activation_roll.value, "condition": self.activation_roll.condition.value},
            "item":            self.item.to_dict() if self.item else None,
        }
    1
class Monster(Card):
    card_type: CardType = CardType.MONSTER
    def __init__(self, card_id: str, name: str, description: str, defeat: RollThreshold, fail: RollThreshold, party_requirement: PartyRequirement) -> None:
        super().__init__(card_id, name, description)
        self.defeat = defeat
        self.fail = fail
        self.party_requirement = party_requirement
        
    def apply_failure(self, game: Game, player: Player) -> None:
        """
        Logic on what happens when the player fails to slay monster..
        """

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

class Item(Card):
    card_type: CardType = CardType.ITEM
    def __init__(self, card_id: str, name: str, description: str, is_cursed: bool = False,) -> None:
        super().__init__(card_id, name, description)
        self.is_cursed = is_cursed
    def to_dict(self):
        return {
            **super().to_dict(),
            "is_cursed": self.is_cursed,
        }
    
class Magic(Card):
    card_type: CardType = CardType.MAGIC
    def __init__(self, card_id: str, name: str, description: str,) -> None:
        super().__init__(card_id, name, description)
    
class Modifier(Card):
    action_cost = 0
    card_type: CardType = CardType.MODIFIER

    def __init__(self, card_id: str, name: str, description: str, options: tuple[int, ...]) -> None:
        super().__init__(card_id, name, description)
        self.options = options

    @property
    def has_choice(self) -> bool:
        return len(self.options) > 1

    def to_dict(self):
        return {
            **super().to_dict(),
            "options": list(self.options),
        }

class Challenge(Card):
    action_cost = 0
    card_type: CardType = CardType.CHALLENGE
    def __init__(self, card_id: str, name: str, description: str) -> None:
        super().__init__(card_id, name, description)

class Leader(Card):
    card_type: CardType = CardType.LEADER
    def __init__(self, card_id: str, name: str, description: str, hero_class: HeroClass) -> None:
        super().__init__(card_id, name, description)
        self.hero_class = hero_class
    def to_dict(self):
        return {
            **super().to_dict(),
            "hero_class": self.hero_class,
        }