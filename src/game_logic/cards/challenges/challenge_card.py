from game_logic.cards.registry import register
from game_logic.base import Challenge
from game_logic.game import Game
from game_logic.player import Player


@register("challenge")
class ChallengeCard(Challenge):
    def __init__(self):
        super().__init__(
            card_id="challenge",
            name="Challenge",
            description=" You may play this card when another player attempts to play a Hero, Item, or Magic card. CHALLENGE that card.",
        )

    def apply(self, game: Game, player: Player) -> None:
        # play_challenge() in game.py owns the full challenge sequence.
        # Card.apply is abstract so we satisfy it here, but it is never called.
        pass
