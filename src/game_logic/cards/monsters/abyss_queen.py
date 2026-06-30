from game_logic.cards.registry import register
from game_logic.base import GameEvent, Monster, RollThreshold, RollCondition, PartyRequirement
from game_logic.game import Game, ChoiceType, Phase
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
    
    # Failure penalty: sacrifice a hero (same re-entrant shape as Arctic Aries).
    def apply_failure(self, game: Game, player: Player) -> None:
        if game.pending_choice is None:
            game.pending_choice = ChoiceType.CHOOSE_HERO_FROM_OWN_PARTY
            game.phase = Phase.AWAITING_CHOICE
            return
        if game.target_hero:
            player.remove_from_party(game.target_hero)
            game.discard_pile.append(game.target_hero)
            game.target_hero = None
            game.pending_choice = None

    # Passive: when an OPPONENT plays a Modifier on your roll, +1. play_modifier
    # only fires MODIFIER_PLAYED when someone else modifies your roll, so the
    # "another player" condition is already handled there — no check needed here.
    def on_event(self, event: GameEvent, game: Game, player: Player) -> None:
        if event == GameEvent.MODIFIER_PLAYED:
            player.current_roll += 1