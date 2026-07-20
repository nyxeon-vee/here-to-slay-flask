from game_logic.cards.registry import register
from game_logic.base import Item, ChoiceType, GameEvent
from game_logic.game import Game
from game_logic.player import Player


@register("suspiciously_shiny_coin")
class SuspiciouslyShinyCoin(Item):
    def __init__(self):
        super().__init__(
            card_id     = "suspiciously_shiny_coin",
            name        = "Suspiciously Shiny Coin",
            description  = "If you successfully roll to use the equipped Hero card's effect, DISCARD a card.",
            is_cursed   = True,
        )

    # No `yield` here! Returning the generator method's CALL is what lets
    # on_event stay a plain function for every other event (see Card.on_event).
    def on_event(self, event: GameEvent, game: Game, player: Player):
        if event is GameEvent.SUCCESSFUL_HERO_ROLL:
            return self._curse_discard(game, player)
        return None

    def _curse_discard(self, game: Game, player: Player):
        # Chained by Hero.finish_roll BEFORE the hero's ability — curse cost
        # is paid first, then the ability resolves.
        if not player.hand:
            game.log_event(f"{player.name} has no cards to discard for {self.name}")
            return
        game.message = f"{self.name}: choose a card to DISCARD"
        card = yield ChoiceType.CHOOSE_CARD_FROM_OWN_HAND
        player.discard(card)
        game.discard_pile.append(card)
        game.log_event(f"{player.name} discarded {card.name} ({self.name}'s curse)", "combat")
        game.message = None
