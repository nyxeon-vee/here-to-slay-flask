from game_logic.cards.registry import register
from game_logic.base import Hero, HeroClass, RollThreshold, RollCondition, ChoiceType
from game_logic.game import Game
from game_logic.player import Player

@register("wildshot")
class Wildshot(Hero):
    def __init__(self):
        super().__init__(
            card_id         = "wildshot",
            name            = "Wildshot",
            description     = "DRAW 3 cards and DISCARD a card.",
            hero_class      = HeroClass.RANGER,
            activation_roll = RollThreshold(8, RollCondition.AT_LEAST),
        )

    def use_ability(self, game: Game, player: Player):
        game.draw_cards(player, 3)
        game.message = "Choose a card to discard!"
        card_to_discard = yield ChoiceType.CHOOSE_CARD_FROM_OWN_HAND
        player.discard(card_to_discard)
        game.message = None