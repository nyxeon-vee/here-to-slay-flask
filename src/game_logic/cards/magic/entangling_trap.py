from game_logic.cards.registry import register
from game_logic.base import Magic, Hero, ChoiceType
from game_logic.game import Game
from game_logic.player import Player

@register("entangling_trap")
class EntanglingTrap(Magic):
    def __init__(self):
        super().__init__(
            card_id         = "entangling_trap",
            name            = "Entangling Trap",
            description     = "DISCARD 2 cards, then STEAL a Hero card.",
        )

    def apply(self, game: Game, player: Player):
        if not len(player.hand) > 2:
            game.log_event(f"{player.name} doesn't have enough cards to discard,{self.name} ability fizzles")
            return
        for _ in range(2):
            game.message =  f"Choose a {"1st" if _ == 0 else "2nd"} card to discard"
            discarded = yield ChoiceType.CHOOSE_CARD_FROM_OWN_HAND
            player.discard(discarded)
        while True:
            target_player, target_hero = yield ChoiceType.CHOOSE_HERO_TO_STEAL
            if not target_player.steal_protected:
                break
            game.message = f"{target_player.name}'s party is protected — choose another hero"
        game.steal_hero(player, target_player, target_hero)
        game.message = None
