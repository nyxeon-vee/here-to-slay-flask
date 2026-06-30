from game_logic.cards.registry import register
from game_logic.base import GameEvent, Monster, RollThreshold, RollCondition, PartyRequirement
from game_logic.game import Game, ChoiceType, Phase
from game_logic.player import Player


# "Each time you roll" = any of the three roll kinds. We match on this set
# instead of adding a separate generic ROLL event, so this monster reacts to all
# of them without the engine needing a new event type.
_ROLL_EVENTS: frozenset = frozenset({GameEvent.HERO_ROLL, GameEvent.MONSTER_ATTACK, GameEvent.CHALLENGE_ROLL})

@register("anuran_cauldron")
class AnuranCauldron(Monster):
    def __init__(self):
        super().__init__(
            card_id             = "anuran_cauldron",
            name                = "Anuran Cauldron",
            description         = "Each time you roll, +1 to your roll.",
            defeat              = RollThreshold(7, RollCondition.AT_LEAST),
            fail                = RollThreshold(6, RollCondition.AT_MOST),
            fail_description    = "SACRIFICE a Hero card",
            party_requirement   = PartyRequirement(3, tuple())
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

    # Passive: +1 to any roll this player makes while this monster is in party.
    def on_event(self, event: GameEvent, game: Game, player: Player) -> None:
        if event in _ROLL_EVENTS:
            player.current_roll += 1