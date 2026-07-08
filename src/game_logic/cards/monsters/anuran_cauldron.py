from game_logic.cards.registry import register
from game_logic.base import GameEvent, Hero, Monster, RollThreshold, RollCondition, PartyRequirement, ChoiceType
from game_logic.game import Game
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

    def apply_failure(self, game: Game, player: Player):
        if not any(isinstance(c, Hero) for c in player.party):
            return  # no heroes to sacrifice — fizzle
        game.message = "Choose a hero to sacrifice"
        sacrifice = yield ChoiceType.CHOOSE_HERO_FROM_OWN_PARTY
        player.remove_from_party(sacrifice)
        game.discard_pile.append(sacrifice)
        game.message = None

    def on_event(self, event: GameEvent, game: Game, player: Player) -> None:
        if event in _ROLL_EVENTS:
            player.current_roll += 1
