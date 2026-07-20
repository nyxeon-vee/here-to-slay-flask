from game_logic.cards.registry import register
from game_logic.base import Item, HeroClass



@register("bard_mask")
class BardMask(Item):
    def __init__(self):
        super().__init__(
            card_id     = "bard_mask",
            name        = "Bard Mask",
            description = "The equipped Hero card is considered a Bard instead of its original class.",
            is_cursed   = False,
        )
        # The class the hero had before the mask went on (per-copy state).
        self.previous_hero_class: HeroClass | None = None

    def on_equip(self):
        if self.owner:
            self.previous_hero_class = self.owner.hero_class
            self.owner.hero_class = HeroClass.BARD


    def on_unequip(self):
        if self.owner and self.previous_hero_class:
            self.owner.hero_class = self.previous_hero_class
