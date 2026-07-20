from game_logic.cards.registry import register
from game_logic.base import Magic, Hero, ChoiceType
from game_logic.game import Game
from game_logic.player import Player

@register("critical_boost")
class CriticalBoost(Magic):
    def __init__(self):
        super().__init__(
            card_id         = "critical_boost",
            name            = "Critical Boost",
            description     = "DRAW 3 cards and DISCARD a card.",
        )

    def apply(self, game: Game, player: Player):
        game.draw_cards(player, 3)
        discarded_card = yield ChoiceType.CHOOSE_CARD_FROM_OWN_HAND
        player.discard(discarded_card)
        