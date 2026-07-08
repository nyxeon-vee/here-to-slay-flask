from game_logic.cards.registry import register
from game_logic.base import Hero, HeroClass, RollThreshold, RollCondition, ChoiceType
from game_logic.game import Game
from game_logic.player import Player

@register("dodgy_dealer")
class DodgyDealer(Hero):
    def __init__(self):
        super().__init__(
            card_id         = "dodgy_dealer",
            name            = "Dodgy Dealer",
            description     = "Trade hands with another player.",
            hero_class      = HeroClass.BARD,
            activation_roll = RollThreshold(9, RollCondition.AT_LEAST),
        )

    def use_ability(self, game: Game, player: Player):
        game.message = "Choose a player to trade hands with"
        target = yield ChoiceType.CHOOSE_TARGET_PLAYER
        player.hand, target.hand = target.hand, player.hand
        game.message = None
