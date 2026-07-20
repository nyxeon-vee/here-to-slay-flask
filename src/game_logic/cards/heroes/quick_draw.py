from game_logic.cards.registry import register
from game_logic.base import Hero, HeroClass, RollThreshold, RollCondition, ChoiceType, Item
from game_logic.game import Game
from game_logic.player import Player

@register("quick_draw")
class QuickDraw(Hero):
    def __init__(self):
        super().__init__(
            card_id         = "quick_draw",
            name            = "Quick Draw",
            description     = "DRAW 2 cards. If at least one of those cards is an item card, you may play one of them immediately.",
            hero_class      = HeroClass.RANGER,
            activation_roll = RollThreshold(8, RollCondition.AT_LEAST),
        )

    def use_ability(self, game: Game, player: Player):
        n = game.draw_cards(player, 2)
        if n == 0:
            return  # deck and discard both empty — nothing drawn
        items: list = [c for c in player.hand[-n:] if isinstance(c, Item)]
        if not items:
            return  # no items among the drawn cards
        # Playing an item needs a hero (in any party) with a free item slot —
        # without one the equip prompt would be unanswerable.
        if not any(
            isinstance(c, Hero) and c.item is None
            for p in game.players for c in p.party
        ):
            game.log_event("No hero has a free item slot — the drawn item stays in hand")
            return

        # "you MAY play one of them" — the play is optional.
        game.message = "Play one of the drawn items immediately?"
        play_it = yield ChoiceType.CHOOSE_YES_NO
        if not play_it:
            game.message = None
            return

        if len(items) == 1:
            chosen = items[0]  # only one candidate — no pick needed
        else:
            game.collected_cards = items
            game.message = "Choose an item to play"
            chosen = yield ChoiceType.CHOOSE_CARD_FROM_POOL
            game.collected_cards = []
        game.message = None
        # Delegate to the item's own generator (its "choose a hero to equip"
        # prompt flows through this one) — same pattern as Hook.
        gen = game._execute_card(player, chosen)
        if gen is not None:
            yield from gen
