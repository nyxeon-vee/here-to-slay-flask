from game_logic.cards.registry import register
from game_logic.base import Hero, HeroClass, RollThreshold, RollCondition, ChoiceType
from game_logic.game import Game
from game_logic.player import Player

@register("sharp_fox")
class SharpFox(Hero):
    def __init__(self):
        super().__init__(
            card_id         = "sharp_fox",
            name            = "Sharp Fox",
            description     = "Look at another player's hand.",
            hero_class      = HeroClass.RANGER,
            activation_roll = RollThreshold(5, RollCondition.AT_LEAST),
        )

    def use_ability(self, game: Game, player: Player):
        if not any(p.hand for p in game.players if p is not player):
            game.log_event(f"No one has cards to look at — {self.name}'s ability fizzles")
            return
        game.message = "Choose a player to look at their hand"
        target = yield ChoiceType.CHOOSE_TARGET_PLAYER
        if not target.hand:
            game.log_event(f"{target.name} has no cards to show!")
            return
        # Reuse the pool prompt as a hand VIEWER: the serializer sends
        # collected_cards only to the answerer, so only we see the hand.
        # COPY the list — collected_cards must never alias another player's
        # actual hand.
        game.collected_cards = list(target.hand)
        game.message = f"{target.name}'s hand — click any card to close"
        _ = yield ChoiceType.CHOOSE_CARD_FROM_POOL  # answer ignored; the prompt IS the viewer
        game.collected_cards = []
        game.message = None
        game.log_event(f"{player.name} looked at {target.name}'s hand")
