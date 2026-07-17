from game_logic.cards.registry import register
from game_logic.base import Magic, Hero, ChoiceType
from game_logic.game import Game
from game_logic.player import Player

@register("call_to_the_fallen")
class CallToTheFallen(Magic):
    def __init__(self):
        super().__init__(
            card_id         = "call_to_the_fallen",
            name            = "Call To The Fallen",
            description     = "Search the discard pile for a Hero card and add it to your hand.",
        )

    def apply(self, game: Game, player: Player):
        # The card leaves the hand and hits the pile up front — a fizzle (no
        # heroes to retrieve) still consumes the card.
        player.hand.remove(self)
        game.discard_pile.append(self)
        pool: list = [c for c in game.discard_pile if isinstance(c, Hero)]
        if not pool:
            return
        game.collected_cards = pool
        game.message = "Choose a hero to retrieve from the discard pile"
        chosen = yield ChoiceType.CHOOSE_CARD_FROM_POOL
        if chosen in game.discard_pile:
            game.discard_pile.remove(chosen)
            player.hand.append(chosen)
            game.log_event(f"{player.name} retrieved {chosen.name} from the discard pile")
        game.collected_cards = []
        game.message = None
