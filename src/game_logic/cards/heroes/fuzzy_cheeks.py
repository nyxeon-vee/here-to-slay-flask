from game_logic.cards.registry import register
from game_logic.base import Hero, HeroClass, RollThreshold, RollCondition, Challenge
from game_logic.game import Game, Phase, ChoiceType
from game_logic.player import Player
import random
@register("fuzzy_cheeks")
class FuzzyCheeks(Hero):
    def __init__(self):
        super().__init__(
            card_id         = "fuzzy_cheeks",
            name            = "Fuzzy Cheeks",
            description     = "DRAW a card and play a Hero card from your hand immediately.",
            hero_class      = HeroClass.BARD,
            activation_roll = RollThreshold(9, RollCondition.AT_LEAST),
        )

    def use_ability(self, game: Game, player: Player) -> None:
        if game.pending_choice is None:
            player.draw(game.deck)
            game.pending_choice = ChoiceType.CHOOSE_CARD_FROM_OWN_HAND
            game.phase = Phase.AWAITING_CHOICE
            return
        chosen = game.target_card
        game.target_card = None
        game.pending_choice = None
        if isinstance(chosen, Hero):
            game._execute_card(player, chosen)
