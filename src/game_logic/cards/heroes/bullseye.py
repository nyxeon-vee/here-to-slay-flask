from game_logic.cards.registry import register
from game_logic.base import Hero, HeroClass, RollThreshold, RollCondition, ChoiceType
from game_logic.game import Game
from game_logic.player import Player

@register("bullseye")
class Bullseye(Hero):
    def __init__(self):
        super().__init__(
            card_id         = "bullseye",
            name            = "Bullseye",
            description     = "Look at the top 3 cards of the deck. Add one to your hand, then return the other two to the top of the deck in any order.",
            hero_class      = HeroClass.RANGER,
            activation_roll = RollThreshold(7, RollCondition.AT_LEAST),
        )

    def use_ability(self, game: Game, player: Player):
        # pool IS collected_cards (same list), so removing from it updates the
        # UI's pool between the two prompts for free.
        pool = [game.deck.pop() for _ in range(min(3, len(game.deck)))]
        if not pool:
            game.log_event("The deck is empty — no cards to look at!")
            return
        game.collected_cards = pool

        game.message = "Choose a card to keep"
        kept = yield ChoiceType.CHOOSE_CARD_FROM_POOL
        pool.remove(kept)
        player.hand.append(kept)

        if len(pool) == 2:
            # The deck's top is the END of the list — append the other card
            # first so the chosen one ends up on top (drawn next).
            game.message = "Choose which card goes on TOP of the deck (drawn next)"
            top = yield ChoiceType.CHOOSE_CARD_FROM_POOL
            pool.remove(top)
            game.deck.append(pool.pop())
            game.deck.append(top)
        else:
            game.deck.extend(pool)  # 0 or 1 card left — no order to choose
            pool.clear()

        game.collected_cards = []
        game.message = None
