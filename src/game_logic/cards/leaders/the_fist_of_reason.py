from game_logic.cards.registry import register
from game_logic.base import Leader, HeroClass, GameEvent
from game_logic.game import Game
from game_logic.player import Player
@register("the_fist_of_reason")
class TheFistOfReason(Leader):  # was mistakenly named TheDivineArrow (copy-paste)
    def __init__(self):
        super().__init__(
            card_id         = "the_fist_of_reason",
            name            = "The Fist of Reason",
            description     = "Each time you roll to CHALLENGE, +2 to your roll.",
            hero_class      = HeroClass.FIGHTER,
        )

    # Passive: Game fires CHALLENGE_ROLL right after this player rolls in a
    # challenge (see start_challenge / close_challenge_roll_1), so the +2 lands
    # on the correct roll even when it's an opponent challenging.
    def on_event(self, event: GameEvent, game: Game, player: Player) -> None:
        if event == GameEvent.CHALLENGE_ROLL:
            player.current_roll += 2