from game_logic.cards.registry import register
from game_logic.base import Hero, HeroClass, RollThreshold, RollCondition
from game_logic.game import Game, Phase, ChoiceType
from game_logic.player import Player
@register("dodgy_dealer")
class DodgyDealer(Hero):
    def __init__(self):
        super().__init__(
            card_id         = "dodgy_dealer",
            name            = "Dodgy Dealer",
            description     = "Trade hands with another player.",
            hero_class      = HeroClass.BARD,
            activation_roll = RollThreshold(9, RollCondition.AT_LEAST),
        )

    def use_ability(self, game: Game, player: Player) -> None:
        # 1st call: ask which player to trade hands with.
        if game.target_player is None:
            game.pending_choice = ChoiceType.CHOOSE_TARGET_PLAYER
            game.phase = Phase.AWAITING_CHOICE
            return

        # 2nd call: swap the two hand lists in one tuple-assignment.
        player.hand, game.target_player.hand = game.target_player.hand, player.hand
        game.target_player = None
        game.pending_choice = None  # signal "done" so submit_choice finalizes
