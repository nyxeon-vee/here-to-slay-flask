from game_logic.cards.registry import register
from game_logic.base import Monster, RollThreshold, RollCondition, PartyRequirement
from game_logic.game import Game
from game_logic.player import Player
@register("")
class AbyssQueen(Monster):
    def __init__(self):
        super().__init__(
            card_id             = "abyss_queen",
            name                = "Abyss Queen",
            description         = "Each time another player plays a Modifier card on one of your rolls, +1 to your roll.",
            defeat              = RollThreshold(8, RollCondition.AT_LEAST),
            fail                = RollThreshold(5, RollCondition.AT_MOST),
            party_requirement   = PartyRequirement(2, tuple())
        )

