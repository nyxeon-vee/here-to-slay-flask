from game_logic.cards.registry import register
from game_logic.base import Hero, HeroClass, RollThreshold, RollCondition, ChoiceType
from game_logic.game import Game
from game_logic.player import Player

@register("qi_bear")
class QiBear(Hero):
    def __init__(self):
        super().__init__(
            card_id         = "qi_bear",
            name            = "Qi Bear",
            description     = "DISCARD up to 3 cards. For each card discarded, DESTROY a Hero card. ",
            hero_class      = HeroClass.FIGHTER,
            activation_roll = RollThreshold(10, RollCondition.AT_LEAST),
        )

    def use_ability(self, game: Game, player: Player):
        if not player.hand:
            return
        if not game.has_destroyable_opponent_heroes(player):
            game.log_event(f"No destroyable heroes — {self.name}'s ability fizzles")
            return
        game.message = "How many cards to discard? (0–3)"
        count = yield ChoiceType.CHOOSE_NUMBER
        count = max(0, min(3, count))
        for _ in range(count):
            if not player.hand:
                break
            if not game.has_destroyable_opponent_heroes(player):
                break  # last destroy used up all valid targets
            game.message = "Choose a card to discard"
            discard_card = yield ChoiceType.CHOOSE_CARD_FROM_OWN_HAND
            game.message = "Choose a hero to destroy"
            while True:
                target_player, target_hero = yield ChoiceType.CHOOSE_HERO_TO_DESTROY
                if not target_player.destroy_protected:
                    break
                game.message = f"{target_player.name}'s party is protected — choose another hero"
            player.discard(discard_card)
            game.discard_pile.append(discard_card)
            game.destroy_hero(target_player, target_hero)
        game.message = None
