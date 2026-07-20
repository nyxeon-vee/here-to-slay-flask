from game_logic.cards.registry import register
from game_logic.base import Magic, Hero, ChoiceType
from game_logic.game import Game
from game_logic.player import Player

@register("forced_exchange")
class ForcedExchange(Magic):
    def __init__(self):
        super().__init__(
            card_id         = "forced_exchange",
            name            = "Forced Exchange",
            description     = "STEAL a Hero card from that player's Party, then move a Hero card from your Party to that player's Party.",
        )

    def apply(self, game: Game, player: Player):
        # Only unprotected opponents with heroes are valid — if none, fizzle so
        # the game doesn't softlock on an unanswerable prompt.
        if not game.has_stealable_opponent_heroes(player):
            game.log_event(f"No player has stealable heroes, {self.name} ablility fizzles!")
            return
        if not any(isinstance(c, Hero) for c in player.party):
            game.log_event(f"{player.name} has no heroes, {self.name} ablility fizzles!")
        # The UI greys out protected parties for CHOOSE_HERO_TO_STEAL, but a
        # stale/naughty client could still submit one — re-prompt until valid.
        game.message = "Choose a hero to steal from an opponent's party"
        while True:
            target_player, target_hero = yield ChoiceType.CHOOSE_HERO_TO_STEAL
            if not target_player.steal_protected:
                break
            game.message = f"{target_player.name}'s party is protected — choose another hero"
        game.steal_hero(player, target_player, target_hero)
        chosen_hero = yield ChoiceType.CHOOSE_HERO_FROM_OWN_PARTY
        player.remove_from_party(chosen_hero)
        target_player.add_to_party(chosen_hero)
        game.log_event(f"{self.name} moved to {target_player.name}'s party")
        game.message = None