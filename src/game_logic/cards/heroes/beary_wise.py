from game_logic.cards.registry import register
from game_logic.base import Hero, HeroClass, RollThreshold, RollCondition
from game_logic.game import Game, Phase, ChoiceType
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

    def use_ability(self, game: Game, player: Player) -> None:
        # Two-phase, multi-player ability. It's re-entered once per opponent and
        # then once more for the active player:
        #   pending_targets       = the opponents still to discard (a work queue)
        #   pending_choice_player = WHO the UI should prompt right now
        #   collected_cards       = the pool of discarded cards to choose from
        # Phase A (CHOOSE_CARD_FROM_OWN_HAND): walk the queue, each opponent
        #   discards one card into the pool. Phase B (CHOOSE_CARD_FROM_POOL): the
        #   active player keeps one from the pool; the rest hit the discard pile.
        if game.pending_choice is None:
            # First entry: build the queue of opponents who actually have cards.
            game.pending_targets = [p for p in game.players if p is not player and p.hand]
            game.collected_cards = []
            game.pending_choice = ChoiceType.CHOOSE_CARD_FROM_OWN_HAND

        if game.pending_choice == ChoiceType.CHOOSE_CARD_FROM_OWN_HAND:
            # Process previous opponent's choice
            if game.target_card is not None:
                done_player = game.pending_targets.pop(0)
                done_player.discard(game.target_card)
                game.collected_cards.append(game.target_card)
                game.target_card = None
                game.pending_choice_player = None

            # Ask next opponent
            if game.pending_targets:
                game.pending_choice_player = game.pending_targets[0]
                game.phase = Phase.AWAITING_CHOICE
                return

            # All opponents done — active player picks one to keep
            if game.collected_cards:
                game.pending_choice = ChoiceType.CHOOSE_CARD_FROM_POOL
                game.pending_choice_player = player
                game.phase = Phase.AWAITING_CHOICE
                return

            game.pending_choice = None
            return

        # Active player chose from pool
        if game.target_card in game.collected_cards:
            game.collected_cards.remove(game.target_card)
            player.hand.append(game.target_card)
        game.discard_pile.extend(game.collected_cards)
        game.collected_cards = []
        game.target_card = None
        game.pending_choice_player = None
        game.pending_choice = None
