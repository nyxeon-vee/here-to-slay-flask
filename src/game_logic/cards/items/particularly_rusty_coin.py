from game_logic.cards.registry import register
from game_logic.base import Item, ChoiceType, GameEvent
from game_logic.game import Game
from game_logic.player import Player


@register("particularly_rusty_coin")
class ParticularlyRustyCoin(Item):
    def __init__(self):
        super().__init__(
            card_id     = "particularly_rusty_coin",
            name        = "Particularly Rusty Coin",
            description  = "If you unsuccessfully roll to use the equipped Hero card's effect, DRAW a card.",
            is_cursed   = False,
        )

    def on_event(self, event: GameEvent, game: Game, player: Player) -> None:
        # Fired by Hero.finish_roll when the hero this coin is equipped to fails its roll.
        if event is GameEvent.UNSUCCESSFUL_HERO_ROLL and game.deck:
            player.draw(game.deck)
