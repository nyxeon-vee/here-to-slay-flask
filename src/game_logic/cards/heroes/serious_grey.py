from game_logic.cards.registry import register
from game_logic.base import Hero, HeroClass, RollThreshold, RollCondition, ChoiceType
from game_logic.game import Game
from game_logic.player import Player

@register("serious_grey")
class SeriousGrey(Hero):
    def __init__(self):
        super().__init__(
            card_id         = "serious_grey",
            name            = "Serious Grey",
            description     = "DESTROY a Hero and DRAW a card.",
            hero_class      = HeroClass.RANGER,
            activation_roll = RollThreshold(9, RollCondition.AT_LEAST),
        )

    def use_ability(self, game: Game, player: Player):
        if not game.has_destroyable_opponent_heroes(player):
            game.log_event(f"No destroyable heroes — {self.name}'s ability fizzles")
            return
        # The UI greys out destroy_protected parties, but a stale/naughty client
        # could still submit one — re-prompt until the target is valid.
        game.message = "Choose a hero to destroy!"
        while True:
            target_player, target_hero = yield ChoiceType.CHOOSE_HERO_TO_DESTROY
            if not target_player.destroy_protected:
                break
            game.message = f"{target_player.name}'s party is protected — choose another hero"
        game.destroy_hero(target_player, target_hero)
        game.message = None
        game.draw_cards(player)