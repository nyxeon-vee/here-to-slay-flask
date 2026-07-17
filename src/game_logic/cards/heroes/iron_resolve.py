from game_logic.base import Hero, HeroClass, RollThreshold, RollCondition
from game_logic.cards.registry import register
from game_logic.game import Game
from game_logic.player import Player


@register("iron_resolve")
class IronResolve(Hero):
    def __init__(self) -> None:
        super().__init__(
            card_id         = "iron_resolve",
            name            = "Iron Resolve",
            description     = "Cards you play cannot be challenged for the rest of your turn.",
            hero_class      = HeroClass.GUARDIAN,
            activation_roll = RollThreshold(8, RollCondition.AT_LEAST),
        )
    def use_ability(self, game: Game, player: Player):
        player.challenge_protected = True
        game.log_event(f"{player.name}'s cards cannot be challenged for the rest of their turn")