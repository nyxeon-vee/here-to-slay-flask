from game_logic.cards.registry import register
from game_logic.base import Hero, HeroClass, RollThreshold, RollCondition, ChoiceType, Item
from game_logic.game import Game
from game_logic.player import Player

@register("lookie_rooke")
class LookieRookie(Hero):
    def __init__(self):
        super().__init__(
            card_id         = "lookie_rookie",
            name            = "Lookie Rookie",
            description     = "Search the discard pile for an item card and add it to your hand.",
            hero_class      = HeroClass.RANGER,
            activation_roll = RollThreshold(5, RollCondition.AT_LEAST),
        )

    def use_ability(self, game: Game, player: Player):
        if not any(isinstance(c, Item) for c in game.discard_pile):
            game.log_event("Discard pile doesn't have any items")
            return
        pool = []
        for card in game.discard_pile:
            if isinstance(card, Item):
                pool.append(card)
        game.collected_cards = pool
        game.message = "Choose item to add to your hand"
        chosen_item = yield ChoiceType.CHOOSE_CARD_FROM_POOL
        player.hand.append(chosen_item)
        game.discard_pile.remove(chosen_item)
        game.collected_cards = []
        game.message = ""
            