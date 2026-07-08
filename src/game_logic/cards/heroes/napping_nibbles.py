from game_logic.cards.registry import register
from game_logic.base import Hero, HeroClass, RollThreshold, RollCondition, ChoiceType
from game_logic.game import Game
from game_logic.player import Player

@register("napping_nibbles")
class NappingNibbles(Hero):
    def __init__(self):
        super().__init__(
            card_id         = "napping_nibbles",
            name            = "Napping Nibbles",
            description     = "Do nothing.",
            hero_class      = HeroClass.BARD,
            activation_roll = RollThreshold(2, RollCondition.AT_LEAST),
        )

    def use_ability(self, game: Game, player: Player):
        # Doing nothing
        return
