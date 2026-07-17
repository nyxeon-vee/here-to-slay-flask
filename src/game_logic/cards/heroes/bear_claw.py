from game_logic.cards.registry import register
from game_logic.base import Hero, HeroClass, RollThreshold, RollCondition, ChoiceType
from game_logic.game import Game
from game_logic.player import Player
import random

@register("bear_claw")
class BearClaw(Hero):
    def __init__(self):
        super().__init__(
            card_id         = "bear_claw",
            name            = "Bear Claw",
            description     = "Pull a card from another player's hand. If it is a Hero card, pull a second card from that player's hand.",
            hero_class      = HeroClass.FIGHTER,
            activation_roll = RollThreshold(7, RollCondition.AT_LEAST),
        )

    def use_ability(self, game: Game, player: Player):
        if not any(p.hand for p in game.players if p is not player):
            game.log_event(f"No one has cards! {self.name}'s ability fizzled!")
            return  # no one has cards — fizzle
        game.message = "Choose a player to pull a card from"
        target = yield ChoiceType.CHOOSE_TARGET_PLAYER
        if not target.hand:
            game.message = None
            return
        first = random.choice(target.hand)
        target.hand.remove(first)
        player.hand.append(first)
        if isinstance(first, Hero) and target.hand:
            second = random.choice(target.hand)
            target.hand.remove(second)
            player.hand.append(second)
        game.message = None
