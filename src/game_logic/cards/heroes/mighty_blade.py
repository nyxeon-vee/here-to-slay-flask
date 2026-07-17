from game_logic.base import Hero, HeroClass, RollThreshold, RollCondition
from game_logic.cards.registry import register
from game_logic.game import Game
from game_logic.player import Player


@register("mighty_blade")
class MightyBlade(Hero):
    def __init__(self) -> None:
        super().__init__(
            card_id         = "mighty_blade",
            name            = "Mighty Blade",
            description     = "Hero cards in your Party cannot be destroyed until your next turn.",
            hero_class      = HeroClass.GUARDIAN,
            activation_roll = RollThreshold(8, RollCondition.AT_LEAST),
        )
    def use_ability(self, game: Game, player: Player):
        player.destroy_protected = True
        game.log_event(f"{player.name}'s heroes cannot be destroyed until their next turn")