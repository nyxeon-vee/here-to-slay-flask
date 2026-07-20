from game_logic.cards.registry import register
from game_logic.base import Hero, Item, ChoiceType, HeroClass
from game_logic.game import Game
from game_logic.player import Player


@register("fighter_mask")
class FighterMask(Item):
    def __init__(self):
        super().__init__(
            card_id     = "fighter_mask",
            name        = "Fighter Mask",
            description = "The equipped Hero card is considered a Fighter instead of its original class.",
            is_cursed   = False,
        )
        # The class the hero had before the mask went on (per-copy state).
        self.previous_hero_class: HeroClass | None = None

    def on_equip(self):
        if self.owner:
            self.previous_hero_class = self.owner.hero_class
            self.owner.hero_class = HeroClass.FIGHTER


    def on_unequip(self):
        if self.owner and self.previous_hero_class:
            self.owner.hero_class = self.previous_hero_class
