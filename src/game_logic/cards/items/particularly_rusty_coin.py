from game_logic.cards.registry import register
from game_logic.base import Item, Phase, ChoiceType, GameEvent
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

    def apply(self, game: Game, player: Player) -> None:
        # Playing an item EQUIPS it to a hero. Re-entrant like every other effect:
        # 1st call asks which hero, 2nd call (target_hero filled) attaches it.
        if game.target_hero is None:
            game.pending_choice = ChoiceType.CHOOSE_HERO_FROM_ANY_PARTY
            game.phase = Phase.AWAITING_CHOICE
            return
        # Move the item out of the hand and onto the chosen hero.
        if self in player.hand:
            player.hand.remove(self)
        game.target_hero.add_item(self)
        game.target_hero = None
        game.pending_choice = None   # signal "done" so the resume logic finalizes

    def on_event(self, event: GameEvent, game: Game, player: Player) -> None:
        # Fired by Hero.apply when the hero this coin is equipped to fails its roll.
        if event is GameEvent.UNSUCCESSFUL_HERO_ROLL and game.deck:
            player.draw(game.deck)
