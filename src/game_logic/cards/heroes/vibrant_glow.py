from game_logic.base import Hero, HeroClass, RollThreshold, RollCondition
from game_logic.cards.registry import register
from game_logic.game import Game
from game_logic.player import Player


@register("vibrant_glow")
class VibrantGlow(Hero):
    def __init__(self) -> None:
        super().__init__(
            card_id         = "vibrant_glow",
            name            = "Vibrant Glow",
            description     = "+5 to all your rolls until the end of your turn.",
            hero_class      = HeroClass.GUARDIAN,
            activation_roll = RollThreshold(9, RollCondition.AT_LEAST),
        )

    def use_ability(self, game: Game, player: Player):
        # Flat bonus applied inside Game.roll_dice; += so multiple boosts stack.
        # Cleared in Game.end_turn ("until the END of your turn").
        player.roll_bonus += 5
        game.log_event(f"{player.name} gets +5 to all rolls until the end of their turn", "good")
