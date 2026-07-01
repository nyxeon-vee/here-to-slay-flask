from game_logic.cards.registry import register
from game_logic.base import Modifier
from game_logic.game import Game
from game_logic.player import Player


def _mod(card_id, name, description, options):
    """Factory that produces a registered Modifier class."""
    def apply(self, game: Game, player: Player) -> None:
        pass  # play_modifier() in game.py handles everything

    cls = type(name.replace(" ", ""), (Modifier,), {"apply": apply})
    cls.__init__ = lambda self: Modifier.__init__(
        self, card_id=card_id, name=name, description=description, options=options
    )
    return register(card_id)(cls)


ModP1M3 = _mod("mod_p1m3", "Modifier +1/-3", "Add +1 OR -3 to any roll in progress.", (1, -3))
ModP2M2 = _mod("mod_p2m2", "Modifier +2/-2", "Add +2 OR -2 to any roll in progress.", (2, -2))
ModP3M1 = _mod("mod_p3m1", "Modifier +3/-1", "Add +3 OR -1 to any roll in progress.", (3, -1))
ModP4   = _mod("mod_p4",   "Modifier +4",    "Add +4 to any roll in progress.",        (4,))
ModM4   = _mod("mod_m4",   "Modifier -4",    "Subtract 4 from any roll in progress.", (-4,))
