from game_logic.cards.registry import register
from game_logic.base import Leader, HeroClass, GameEvent
from game_logic.game import Game
from game_logic.player import Player
@register("the_cloaked_sage")
class TheCloakedSage(Leader):
    def __init__(self):
        super().__init__(
            card_id         = "the_cloaked_sage",
            name            = "The Cloaked Sage",
            description     = "Each time you play a Magic card, DRAW a card.",
            hero_class      = HeroClass.WIZARD,
        )

    def on_event(self, event: GameEvent, game: Game, player: Player) -> None:
            if event == GameEvent.MAGIC_PLAYED:
                player.draw(game.deck)