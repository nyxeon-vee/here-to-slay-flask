from game_logic.cards.registry import register
from game_logic.base import Hero, HeroClass, RollThreshold, RollCondition, Challenge
from game_logic.game import Game, Phase, ChoiceType
from game_logic.player import Player
import random
@register("qi_bear")
class QiBear(Hero):
    def __init__(self):
        super().__init__(
            card_id         = "qi_bear",
            name            = "Qi Bear",
            description     = "DISCARD up to 3 cards. For each card discarded, DESTROY a Hero card. ",
            hero_class      = HeroClass.FIGHTER,
            activation_roll = RollThreshold(10, RollCondition.AT_LEAST),
        )

    def use_ability(self, game: Game, player: Player) -> None:
        if not player.hand:
            return

        if game.pending_choice is None:
            game.pending_choice = ChoiceType.CHOOSE_NUMBER
            game.phase = Phase.AWAITING_CHOICE
            return

        # game.choice holds how many pairs remain
        while game.choice and game.choice > 0 and player.hand:
            if game.target_card is None:
                game.pending_choice = ChoiceType.CHOOSE_CARD_FROM_OWN_HAND
                game.phase = Phase.AWAITING_CHOICE
                return
            if game.target_hero is None:
                game.pending_choice = ChoiceType.CHOOSE_HERO_FROM_OPPONENT_PARTY
                game.phase = Phase.AWAITING_CHOICE
                return
            # one pair complete
            player.discard(game.target_card)
            game.target_player.remove_from_party(game.target_hero)
            game.discard_pile.append(game.target_hero)
            game.target_card = None
            game.target_hero = None
            game.target_player = None
            game.choice -= 1

        game.choice = None
        game.pending_choice = None