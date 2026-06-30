from game_logic.cards.registry import register
from game_logic.base import Hero, HeroClass, RollThreshold, RollCondition
from game_logic.game import Game, Phase, ChoiceType
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

    def use_ability(self, game: Game, player: Player) -> None:
        # 1st call: draw a card, then ask which hand card to play for free.
        if game.pending_choice is None:
            player.draw(game.deck)
            game.pending_choice = ChoiceType.CHOOSE_CARD_FROM_OWN_HAND
            game.phase = Phase.AWAITING_CHOICE
            return
        # 2nd call: clear the scratchpad FIRST, then play the chosen hero. Order
        # matters — _execute_card runs another hero's apply(), which reuses these
        # same game.target_*/pending_choice fields, so they must be reset before.
        chosen = game.target_card
        game.target_card = None
        game.pending_choice = None
        if isinstance(chosen, Hero):
            game._execute_card(player, chosen)
