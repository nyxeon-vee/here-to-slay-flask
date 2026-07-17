from game_logic.cards.registry import register
from game_logic.base import Hero, HeroClass, RollThreshold, RollCondition
from game_logic.game import Game
from game_logic.player import Player

@register("calming_voice")
class CalmingVoice(Hero):
    def __init__(self):
        super().__init__(
            card_id         = "calming_voice",
            name            = "Calming Voice",
            description     = "Hero cards in your Party cannot be stolen until your next turn.",
            hero_class      = HeroClass.GUARDIAN,
            activation_roll = RollThreshold(9, RollCondition.AT_LEAST),
        )

    def use_ability(self, game: Game, player: Player):
        # No input needed — a plain body (no yield) works fine for the engine.
        # The flag is checked by stealing cards (steal_hero verb) and cleared
        # in Game.start_turn when this player's next turn begins.
        player.steal_protected = True
        game.log_event(f"{player.name}'s party is protected from stealing until their next turn")
