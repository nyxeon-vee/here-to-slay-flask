from game_logic.cards.registry import register
from game_logic.base import Hero, HeroClass, RollThreshold, RollCondition, ChoiceType
from game_logic.game import Game
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

    def use_ability(self, game: Game, player: Player):
        if not any(
            any(isinstance(c, Hero) for c in p.party)
            for p in game.players if p is not player
        ):
            return  # no targets — fizzle
        game.message = "Choose a hero to destroy!"
        target_player, target_hero = yield ChoiceType.CHOOSE_HERO_FROM_OPPONENT_PARTY
        target_player.remove_from_party(target_hero)
        game.discard_pile.append(target_hero)
        game.message = None
