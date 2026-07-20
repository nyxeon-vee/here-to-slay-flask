from game_logic.cards.registry import register
from game_logic.base import Hero, HeroClass, RollThreshold, RollCondition, ChoiceType, Item
from game_logic.game import Game
from game_logic.player import Player

@register("hook")
class Hook(Hero):
    def __init__(self):
        super().__init__(
            card_id         = "hook",
            name            = "Hook",
            description     = "Play an item card from your hand immediately and DRAW a card.",
            hero_class      = HeroClass.RANGER,
            activation_roll = RollThreshold(6, RollCondition.AT_LEAST),
        )

    def use_ability(self, game: Game, player: Player):
        # Card-text order: play the item FIRST, then draw — so the card you
        # draw can't be the item you play.
        items: list = [c for c in player.hand if isinstance(c, Item)]
        free_hero = any(isinstance(c, Hero) and c.item is None for c in player.party)

        if items and free_hero:
            game.collected_cards = items
            game.message = "Choose an item to play"
            chosen = yield ChoiceType.CHOOSE_CARD_FROM_POOL
            # Clear the pool BEFORE delegating — the item opens its own prompt.
            game.collected_cards = []
            game.message = None
            # `yield from` forwards the item's own "choose a hero to equip"
            # prompt through this generator; the engine can't tell the difference.
            gen = game._execute_card(player, chosen)
            if gen is not None:
                yield from gen
        elif not items:
            game.log_event(f"{player.name} has no Item card to play")
        else:
            game.log_event(f"{player.name} has no hero free to equip an item")

        # The draw is unconditional — the text says "and DRAW", not "If you do".
        if game.draw_cards(player):
            game.log_event(f"{player.name} drew a card")
