from game_logic.cards.registry import register
from game_logic.base import Hero, HeroClass, RollThreshold, RollCondition, Challenge
from game_logic.game import Game, Phase, ChoiceType
from game_logic.player import Player
import random
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

    def use_ability(self, game: Game, player: Player) -> None:
        if game.target_player is None:
            game.pending_choice = ChoiceType.CHOOSE_TARGET_PLAYER
            game.phase = Phase.AWAITING_CHOICE
            return

        player.hand, game.target_player.hand = game.target_player.hand, player.hand
        game.target_player = None
