from game_logic.cards.registry import register
from game_logic.base import Leader, HeroClass, GameEvent
from game_logic.game import Game
from game_logic.player import Player
@register("the_fist_of_reason")
class TheDivineArrow(Leader):
    def __init__(self):
        super().__init__(
            card_id         = "the_fist_of_reason",
            name            = "The Fist of Reason",
            description     = "Each time you roll to CHALLENGE, +2 to your roll.",
            hero_class      = HeroClass.FIGHTER,
        )

    def on_event(self, event: GameEvent, game: Game, player: Player) -> None:
        if event == GameEvent.CHALLENGE_ROLL:
            player.current_roll += 2