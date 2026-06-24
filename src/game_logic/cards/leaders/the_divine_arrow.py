from game_logic.cards.registry import register
from game_logic.base import Leader, HeroClass, GameEvent
from game_logic.game import Game
from game_logic.player import Player
@register("the_divine_arrow")
class TheDivineArrow(Leader):
    def __init__(self):
        super().__init__(
            card_id         = "the_divine_arrow",
            name            = "The Divine Arrow",
            description     = "Each time you roll to ATTACK a Monster card, +1 to your roll.",
            hero_class      = HeroClass.RANGER,
        )

    def on_event(self, event: GameEvent, game: Game, player: Player) -> None:
        if event == GameEvent.MONSTER_ATTACK:
            player.current_roll += 1