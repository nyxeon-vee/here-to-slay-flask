from game_logic.cards.registry import register
from game_logic.base import Hero, HeroClass, RollThreshold, RollCondition, Challenge, ChoiceType
from game_logic.game import Game
from game_logic.player import Player

@register("pan_chucks")
class PanChucks(Hero):
    def __init__(self):
        super().__init__(
            card_id         = "pan_chucks",
            name            = "Pan Chucks",
            description     = "DRAW 2 cards. If at least one of those cards is a Challenge card, you may reveal it, then DESTROY a Hero card.",
            hero_class      = HeroClass.FIGHTER,
            activation_roll = RollThreshold(8, RollCondition.AT_LEAST),
        )

    def use_ability(self, game: Game, player: Player):
        player.draw(game.deck)
        player.draw(game.deck)
        drawn = player.hand[-2:]
        if not any(isinstance(c, Challenge) for c in drawn):
            return  # no Challenge drawn — bonus can't happen
        game.message = "Reveal a Challenge card and destroy a hero?"
        reveal = yield ChoiceType.CHOOSE_YES_NO
        if not reveal:
            game.message = None
            return
        if not game.has_destroyable_opponent_heroes(player):
            game.message = None
            game.log_event(f"No destroyable heroes — {self.name}'s bonus fizzles")
            return  # no valid targets — skip prompt
        game.message = "Choose a hero to destroy"
        while True:
            target_player, target_hero = yield ChoiceType.CHOOSE_HERO_TO_DESTROY
            if not target_player.destroy_protected:
                break
            game.message = f"{target_player.name}'s party is protected — choose another hero"
        game.destroy_hero(target_player, target_hero)
        game.message = None
