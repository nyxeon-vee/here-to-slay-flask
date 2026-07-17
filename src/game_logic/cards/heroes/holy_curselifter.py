from game_logic.base import Hero, HeroClass, RollThreshold, Item, RollCondition, ChoiceType
from game_logic.cards.registry import register
from game_logic.game import Game
from game_logic.player import Player


@register("holy_curselifter")
class HolyCurselifter(Hero):
    def __init__(self) -> None:
        super().__init__(
            card_id         = "holy_curselifter",
            name            = "Holy Curselifter",
            description     = "Return a Cursed Item card equipped to a Hero card in your Party to your hand",
            hero_class      = HeroClass.GUARDIAN,
            activation_roll = RollThreshold(5, RollCondition.AT_LEAST),
        )
    def use_ability(self, game: Game, player: Player):
        has_cursed_item = False
        for card in player.party:
            if isinstance(card, Hero) and isinstance(card.item, Item) and card.item.is_cursed:
                has_cursed_item = True
        
        if not has_cursed_item:
            game.log_event(f"{player.name}'s party doesn't hold a cursed item!")
            return
        game.message = "Choose cursed item to remove from your hero!"
        chosen_hero, chosen_item = yield ChoiceType.CHOOSE_CURSED_ITEM_FROM_OWN_PARTY
        player.hand.append(chosen_item)
        chosen_hero.item = None
        game.message = None