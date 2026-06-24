from game_logic.cards.registry import register
from game_logic.base import Hero, HeroClass, RollThreshold, RollCondition
from game_logic.game import Game, Phase, ChoiceType
from game_logic.player import Player
@register("bad_axe")
class BadAxe(Hero):
    def __init__(self):
        super().__init__(
            card_id         = "bad_axe",
            name            = "Bad Axe",
            description     = "Destroy a Hero card.",
            hero_class      = HeroClass.FIGHTER,
            activation_roll = RollThreshold(8, RollCondition.AT_LEAST),
        )

    def use_ability(self, game: Game, player: Player) -> None:
        if game.target_player is None or game.target_hero is None:
            game.pending_choice = ChoiceType.CHOOSE_HERO_FROM_OPPONENT_PARTY
            game.phase = Phase.AWAITING_CHOICE
            return
        target_hero = game.target_hero
        game.target_player.remove_from_party(target_hero)
        game.discard_pile.append(target_hero)
        game.target_player = None
        game.target_hero = None