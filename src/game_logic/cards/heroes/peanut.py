from game_logic.cards.registry import register
from game_logic.base import Hero, HeroClass, RollThreshold, RollCondition, ChoiceType
from game_logic.game import Game
from game_logic.player import Player

@register("peanut")
class Peanut(Hero):
    def __init__(self):
        super().__init__(
            card_id         = "peanut",
            name            = "Peanut",
            description     = "DRAW 2 cards.",
            hero_class      = HeroClass.BARD,
            activation_roll = RollThreshold(7, RollCondition.AT_LEAST),
        )

    def use_ability(self, game: Game, player: Player):
        # draw_cards is deck-safe: draws what it can, recycling the discard
        # pile into a fresh deck if the draw pile runs out mid-way.
        game.draw_cards(player, 2)
