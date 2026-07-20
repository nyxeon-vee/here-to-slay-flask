from game_logic.cards.registry import register
from game_logic.base import Magic, Hero, ChoiceType
from game_logic.game import Game
from game_logic.player import Player

@register("enchanted_spell")
class EnchantedSpell(Magic):
    def __init__(self):
        super().__init__(
            card_id         = "enchanted_spell",
            name            = "Enchanted Spell",
            description     = "+2 to all of your rolls until the end of your turn.",
        )

    def apply(self, game: Game, player: Player):
        player.roll_bonus += 2
        game.log_event(f"{player.name} gets +2 to all rolls until the end of their turn", "good")