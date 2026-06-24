from game_logic.cards.registry import register
from game_logic.base import GameEvent, Monster, RollThreshold, RollCondition, PartyRequirement
from game_logic.game import Game, ChoiceType, Phase
from game_logic.player import Player


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

    def on_event(self, event: GameEvent, game: Game, player: Player) -> None:
        if event in _ROLL_EVENTS:
            player.current_roll += 1