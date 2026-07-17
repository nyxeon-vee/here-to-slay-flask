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

    def apply(self, game: Game, player: Player):
        # Playing an item EQUIPS it to a hero (generator ability, like heroes).
        # Re-prompt if the chosen hero already holds an item — add_item would
        # silently destroy the old one otherwise.
        game.message = f"Choose a hero to equip {self.name} to"
        while True:
            target = yield ChoiceType.CHOOSE_HERO_FROM_ANY_PARTY
            if target.item is None:
                break
            game.message = f"{target.name} already holds an item — choose another hero"
        if self in player.hand:
            player.hand.remove(self)
        target.add_item(self)
        game.log_event(f"{player.name} equipped {self.name} to {target.name}")
        game.message = None

    def on_event(self, event: GameEvent, game: Game, player: Player) -> None:
        # Fired by Hero.finish_roll when the hero this coin is equipped to fails its roll.
        if event is GameEvent.UNSUCCESSFUL_HERO_ROLL and game.deck:
            player.draw(game.deck)
