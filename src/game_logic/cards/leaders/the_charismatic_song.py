from game_logic.cards.registry import register
from game_logic.base import Leader, HeroClass, GameEvent
from game_logic.game import Game
from game_logic.player import Player
@register("the_charismatic_song")
class TheCharismaticSong(Leader):
    def __init__(self):
        super().__init__(
            card_id         = "the_charismatic_song",
            name            = "The Charismatic Song",
            description     = "Each time you roll to use a Hero card's effect, +1 to your roll.",
            hero_class      = HeroClass.BARD,
        )

    # Passive: +1 to every roll made to activate a Hero. Fired by Hero.apply
    # right after the dice land, before the roll is evaluated.
    def on_event(self, event: GameEvent, game: Game, player: Player) -> None:
        if event == GameEvent.HERO_ROLL:
            player.current_roll += 1