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
        # Only unprotected opponents with heroes are valid — if none, fizzle so
        # the game doesn't softlock on an unanswerable prompt.
        if not game.has_stealable_opponent_heroes(player):
            return
        # The UI greys out protected parties for CHOOSE_HERO_TO_STEAL, but a
        # stale/naughty client could still submit one — re-prompt until valid.
        game.message = "Choose a hero to steal from an opponent's party"
        while True:
            target_player, target_hero = yield ChoiceType.CHOOSE_HERO_TO_STEAL
            if not target_player.steal_protected:
                break
            game.message = f"{target_player.name}'s party is protected — choose another hero"
        game.steal_hero(player, target_player, target_hero)
        player.remove_from_party(self)
        target_player.add_to_party(self)
        game.log_event(f"{self.name} moved to {target_player.name}'s party")
        game.message = None
