from game_logic.cards.registry import register
from game_logic.base import Hero, HeroClass, RollThreshold, RollCondition, ChoiceType
from game_logic.game import Game
from game_logic.player import Player

@register("greedy_cheeks")
class GreedyCheeks(Hero):
    def __init__(self):
        super().__init__(
            card_id         = "greedy_cheeks",
            name            = "Greedy Cheeks",
            description     = "Each other player must give you a card from their hand.",
            hero_class      = HeroClass.BARD,
            activation_roll = RollThreshold(8, RollCondition.AT_LEAST),
        )

    def use_ability(self, game: Game, player: Player):
        opponents = [p for p in game.players if p is not player and p.hand]
        if not opponents:
            return

        for opp in opponents:
            game.pending_choice_player = opp
            game.message = "Choose a card to give"
            card = yield ChoiceType.CHOOSE_CARD_FROM_OWN_HAND
            opp.discard(card)
            player.hand.append(card)

        game.pending_choice_player = None
        game.message = None
