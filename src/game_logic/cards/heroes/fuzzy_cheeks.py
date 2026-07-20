from game_logic.cards.registry import register
from game_logic.base import Hero, HeroClass, RollThreshold, RollCondition, ChoiceType
from game_logic.game import Game
from game_logic.player import Player

@register("fuzzy_cheeks")
class FuzzyCheeks(Hero):
    def __init__(self):
        super().__init__(
            card_id         = "fuzzy_cheeks",
            name            = "Fuzzy Cheeks",
            description     = "DRAW a card and play a Hero card from your hand immediately.",
            hero_class      = HeroClass.BARD,
            activation_roll = RollThreshold(9, RollCondition.AT_LEAST),
        )

    def use_ability(self, game: Game, player: Player):
        game.draw_cards(player)
        if not any(isinstance(c, Hero) for c in player.hand):
            return  # drew a card but no heroes to play — fizzle
        game.message = "Choose a hero to play immediately!"
        chosen = yield ChoiceType.CHOOSE_CARD_FROM_OWN_HAND
        # Clear message BEFORE _execute_card — the inner hero reuses game.message.
        game.message = None
        if isinstance(chosen, Hero):
            game._execute_card(player, chosen)
