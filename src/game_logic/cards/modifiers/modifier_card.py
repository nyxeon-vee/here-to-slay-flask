from game_logic.cards.registry import register
from game_logic.base import Modifier
from game_logic.game import Game
from game_logic.player import Player


@register("modifier")
class ModifierCard(Modifier):
    def __init__(self):
        super().__init__(
            card_id="modifier",
            name="Modifier",
            description="Add +1 OR -3 to any roll currently in progress.",
            options=(1, -3),
        )

    def apply(self, game: Game, player: Player) -> None:
        # play_modifier() in game.py handles everything (adjusts the roll,
        # removes from hand, discards). Card.apply is abstract so we satisfy
        # it here, but it is never called for modifier cards.
        pass
