from game_logic.cards.registry import register
from game_logic.base import Hero, HeroClass, RollThreshold, RollCondition, Challenge
from game_logic.game import Game, Phase, ChoiceType
from game_logic.player import Player
import random
@register("fury_knuckle")
class FuryKnuckle(Hero):
    def __init__(self):
        super().__init__(
            card_id         = "fury_knuckle",
            name            = "Fury Knuckle",
            description     = "Pull a card from another player's hand. If it is a Challenge card, pull a second card from that player's hand.",
            hero_class      = HeroClass.FIGHTER,
            activation_roll = RollThreshold(5, RollCondition.AT_LEAST),
        )

    def use_ability(self, game: Game, player: Player) -> None:
        if game.target_player is None:
            game.pending_choice = ChoiceType.CHOOSE_TARGET_PLAYER
            game.phase = Phase.AWAITING_CHOICE
            return

        first_card = random.choice(game.target_player.hand)
        game.target_player.hand.remove(first_card)
        player.hand.append(first_card)

        if isinstance(first_card, Challenge) and game.target_player.hand:
            second_card = random.choice(game.target_player.hand)
            game.target_player.hand.remove(second_card)
            player.hand.append(second_card)

        game.target_player = None