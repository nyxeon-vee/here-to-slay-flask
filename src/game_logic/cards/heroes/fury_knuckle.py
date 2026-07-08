from game_logic.cards.registry import register
from game_logic.base import Hero, HeroClass, RollThreshold, RollCondition, Challenge, ChoiceType
from game_logic.game import Game
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

    def use_ability(self, game: Game, player: Player):
        if not any(p.hand for p in game.players if p is not player):
            return  # no one has cards — fizzle
        game.message = "Choose a player to pull a card from"
        target = yield ChoiceType.CHOOSE_TARGET_PLAYER
        if not target.hand:
            game.message = None
            return
        first = random.choice(target.hand)
        target.hand.remove(first)
        player.hand.append(first)
        if isinstance(first, Challenge) and target.hand:
            second = random.choice(target.hand)
            target.hand.remove(second)
            player.hand.append(second)
        game.message = None
