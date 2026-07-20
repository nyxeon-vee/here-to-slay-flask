from game_logic.cards.registry import register
from game_logic.base import Item, GameEvent
from game_logic.game import Game
from game_logic.player import Player


@register("curse_of_snakes_eyes")
class CurseOfTheSnakesEyes(Item):
    def __init__(self):
        super().__init__(
            card_id     = "really_big_ring",
            name        = "Curse of the Snake's Eyes",
            description  = "Each time you roll to use the equipped Hero card's effect, -2 to your roll.",
            is_cursed   = True,
        )

    # Equipping is handled by the shared Item.apply in base.py — items only
    # define their passive.
    def on_event(self, event: GameEvent, game: Game, player: Player) -> None:
        # Fired by Hero.finish_roll when the hero this coin is equipped to fails its roll.
        if event is GameEvent.HERO_ROLL:
            player.current_roll -= 2
