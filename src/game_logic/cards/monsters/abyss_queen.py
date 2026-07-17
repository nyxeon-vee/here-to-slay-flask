from game_logic.cards.registry import register
from game_logic.base import GameEvent, Hero, Monster, RollThreshold, RollCondition, PartyRequirement, ChoiceType
from game_logic.game import Game
from game_logic.player import Player

@register("abyss_queen")
class AbyssQueen(Monster):
    def __init__(self):
        super().__init__(
            card_id             = "abyss_queen",
            name                = "Abyss Queen",
            description         = "Each time another player plays a Modifier card on one of your rolls, +1 to your roll.",
            defeat              = RollThreshold(8, RollCondition.AT_LEAST),
            fail                = RollThreshold(5, RollCondition.AT_MOST),
            fail_description    = "SACRIFICE a Hero card",
            party_requirement   = PartyRequirement(2, tuple())
        )

    def apply_failure(self, game: Game, player: Player):
        if not any(isinstance(c, Hero) for c in player.party):
            return  # no heroes to sacrifice — fizzle
        game.message = "Choose a hero to sacrifice"
        sacrifice = yield ChoiceType.CHOOSE_HERO_FROM_OWN_PARTY
        game.sacrifice_hero(player, sacrifice)
        game.message = None

    def on_event(self, event: GameEvent, game: Game, player: Player) -> None:  # noqa: ARG002
        if event == GameEvent.MODIFIER_PLAYED:
            player.current_roll += 1
