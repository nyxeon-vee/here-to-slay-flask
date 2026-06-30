from game_logic.cards.registry import register
from game_logic.base import Hero, HeroClass, RollThreshold, RollCondition
from game_logic.game import Game, Phase, ChoiceType
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

    def use_ability(self, game: Game, player: Player) -> None:
        # Multi-player queue, re-entered once per opponent. Unlike Beary Wise
        # there's no pool to pick from — every card an opponent gives goes
        # straight into your hand.
        #   pending_targets       = the opponents still to give a card (work queue)
        #   pending_choice_player = WHO the UI should prompt right now
        #   collected_cards       = cards gathered so far, all kept by the player
        if game.pending_choice is None:
            # First entry: build the queue of opponents who actually have cards.
            game.pending_targets = [p for p in game.players if p is not player and p.hand]
            game.collected_cards = []
            game.pending_choice = ChoiceType.CHOOSE_CARD_FROM_OWN_HAND

        # Process the previous opponent's choice (skipped on the first entry,
        # when nothing has been chosen yet).
        if game.target_card is not None:
            done_player = game.pending_targets.pop(0)
            done_player.discard(game.target_card)
            game.collected_cards.append(game.target_card)
            game.target_card = None
            game.pending_choice_player = None

        # Ask the next opponent in the queue.
        if game.pending_targets:
            game.pending_choice_player = game.pending_targets[0]
            game.phase = Phase.AWAITING_CHOICE
            return

        # All opponents done — add every gathered card to the player's hand.
        player.hand.extend(game.collected_cards)
        game.collected_cards = []
        game.pending_choice = None