from game_logic.cards.registry import register
from game_logic.base import Hero, HeroClass, RollThreshold, RollCondition, ChoiceType
from game_logic.game import Game
from game_logic.player import Player

@register("tipsy_tootie")
class TipsyTootie(Hero):
    def __init__(self):
        super().__init__(
            card_id         = "tipsy_tootie",
            name            = "Tipsy Tootie",
            description     = "Choose a player. STEAL a Hero card from that player's Party and move this card to that player's Party.",
            hero_class      = HeroClass.BARD,
            activation_roll = RollThreshold(2, RollCondition.AT_LEAST),
        )

    def use_ability(self, game: Game, player: Player):
        if not any(
            any(isinstance(c, Hero) for c in p.party)
            for p in game.players if p is not player
        ):
            return  # This checks if theres any heroes to steal so the game doesnt softlock
        game.message = "Choose a hero to steal from an opponent's party"
        target_player, target_hero = yield ChoiceType.CHOOSE_HERO_FROM_OPPONENT_PARTY
        target_player.remove_from_party(target_hero)
        player.remove_from_party(self)
        player.add_to_party(target_hero)
        target_player.add_to_party(self)
        game.message = None
