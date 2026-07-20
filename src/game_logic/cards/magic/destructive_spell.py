from game_logic.cards.registry import register
from game_logic.base import Magic, Hero, ChoiceType
from game_logic.game import Game
from game_logic.player import Player

@register("critical_boost")
class CriticalBoost(Magic):
    def __init__(self):
        super().__init__(
            card_id         = "critical_boost",
            name            = "Critical Boost",
            description     = "DISCARD a card, then DESTROY a Hero card.",
        )

    def apply(self, game: Game, player: Player):
        if not game.has_destroyable_opponent_heroes(player):
            game.log_event(f"No destroyable heroes — {self.name}'s ability fizzles")
            return
        if not player.hand:
            game.log_event(f"{player.name} doesnt have any cards in the hand, {self.name} ability fizzles")
        game.message = "Choose a card to discard"
        discarded_card = yield ChoiceType.CHOOSE_CARD_FROM_OWN_HAND
        player.discard(discarded_card)
        game.message = "Choose a hero to destroy!"
        while True:
            target_player, target_hero = yield ChoiceType.CHOOSE_HERO_TO_DESTROY
            if not target_player.destroy_protected:
                break
            game.message = f"{target_player.name}'s party is protected — choose another hero"
        game.destroy_hero(target_player, target_hero)
        game.message = None
        