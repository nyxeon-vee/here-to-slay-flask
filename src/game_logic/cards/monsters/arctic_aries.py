from game_logic.cards.registry import register
from game_logic.base import GameEvent, Monster, RollThreshold, RollCondition, PartyRequirement
from game_logic.game import Game, ChoiceType, Phase
from game_logic.player import Player

@register("arctic_aries")
class ArcticAries(Monster):
    def __init__(self):
        super().__init__(
            card_id             = "artic_aries",
            name                = "Artic Aries",
            description         = "Each time you successfully roll to use a Hero's effect, DRAW a card.",
            defeat              = RollThreshold(10, RollCondition.AT_LEAST),
            fail                = RollThreshold(6, RollCondition.AT_MOST),
            fail_description    = "SACRIFICE a Hero card",
            party_requirement   = PartyRequirement(1, tuple())
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
        if event == GameEvent.SUCCESSFUL_HERO_ROLL and game.deck:
            player.draw(game.deck)