from game_logic.base import Hero, HeroClass, RollThreshold, RollCondition, ChoiceType
from game_logic.cards.registry import register
from game_logic.game import Game, Player


@register("guiding_light")
class GuidingLight(Hero):
    def __init__(self) -> None:
        super().__init__(
            card_id         = "guiding_light",
            name            = "Guiding Light",
            description     = "Search the discard pile for a Hero card and add it to your hand.",
            hero_class      = HeroClass.GUARDIAN,
            activation_roll = RollThreshold(7, RollCondition.AT_LEAST),
        )
    def use_ability(self, game: Game, player: Player):
        if not any(isinstance(c, Hero) for c in game.discard_pile):
            return 
        pool = []
        for card in game.discard_pile:
            if isinstance(card, Hero):
                pool.append(card)
        game.message = "Choose a hero from discard pile"
        game.pending_choice_player = player
        game.collected_cards = pool
        chosen_card = yield ChoiceType.CHOOSE_CARD_FROM_POOL
        game.discard_pile.remove(chosen_card)
        player.hand.append(chosen_card)
        game.message = None
        return