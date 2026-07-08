from game_logic.cards.registry import register
from game_logic.base import Hero, HeroClass, RollThreshold, RollCondition, ChoiceType
from game_logic.game import Game
from game_logic.player import Player

@register("beary_wise")
class BearyWise(Hero):
    def __init__(self):
        super().__init__(
            card_id         = "beary_wise",
            name            = "Beary Wise",
            description     = "Each other player must DISCARD a card. Choose one of the discarded cards and add it to your hand.",
            hero_class      = HeroClass.FIGHTER,
            activation_roll = RollThreshold(7, RollCondition.AT_LEAST),
        )

    def use_ability(self, game: Game, player: Player):
        opponents = [p for p in game.players if p is not player and p.hand]
        if not opponents:
            return

        pool = []
        for opp in opponents:
            game.pending_choice_player = opp
            game.message = "Choose a card to discard"
            card = yield ChoiceType.CHOOSE_CARD_FROM_OWN_HAND
            opp.discard(card)
            pool.append(card)

        if not pool:
            game.pending_choice_player = None
            game.message = None
            return

        game.collected_cards = pool
        game.pending_choice_player = player
        game.message = "Choose a card to keep"
        kept = yield ChoiceType.CHOOSE_CARD_FROM_POOL
        pool.remove(kept)
        player.hand.append(kept)
        game.discard_pile.extend(pool)
        game.collected_cards = []
        game.pending_choice_player = None
        game.message = None
