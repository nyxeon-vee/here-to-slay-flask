from game_logic.cards.registry import register
from game_logic.base import Hero, HeroClass, RollThreshold, RollCondition, ChoiceType
from game_logic.game import Game
from game_logic.player import Player

@register("calming_voice")
class CalmingVoice(Hero):
    def __init__(self):
        super().__init__(
            card_id         = "calming_voice",
            name            = "Calming Voice",
            description     = "Hero cards in your Party cannot be stolen until your next turn.",
            hero_class      = HeroClass.GUARDIAN,
            activation_roll = RollThreshold(9, RollCondition.AT_LEAST),
        )

    def use_ability(self, game: Game, player: Player):
        # Todo
        return
