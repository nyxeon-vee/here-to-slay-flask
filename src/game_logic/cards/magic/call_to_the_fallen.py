from game_logic.cards.registry import register
from game_logic.base import Magic, Hero
from game_logic.game import Game, Phase, ChoiceType
from game_logic.player import Player
@register("call_to_the_fallen")
class CallToTheFallen(Magic):
    def __init__(self):
        super().__init__(
            card_id         = "call_to_the_fallen",
            name            = "Call To The Fallen",
            description     = "Search the discard pile for a Hero card and add it to your hand.",
        )
    def apply(self, game: Game, player: Player) -> None:
        # 1st call: gather the Heroes sitting in the discard pile into the pool
        # the UI will show. Nothing to retrieve? The card just fizzles.
        if game.pending_choice is None:
            game.collected_cards = [c for c in game.discard_pile if isinstance(c, Hero)]
            if not game.collected_cards:
                return
            game.pending_choice = ChoiceType.CHOOSE_CARD_FROM_POOL
            game.phase = Phase.AWAITING_CHOICE
            return

        # 2nd call: move the chosen hero out of the discard pile into the hand.
        if game.target_card and game.target_card in game.discard_pile:
            game.discard_pile.remove(game.target_card)
        player.hand.append(game.target_card)
        game.collected_cards = []
        game.target_card = None
        game.pending_choice = None