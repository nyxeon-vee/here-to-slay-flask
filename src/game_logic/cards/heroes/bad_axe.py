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
        # Simplest re-entrant ability (one question):
        #  1st call  -> no target picked yet, so open the prompt and bail.
        #  2nd call  -> target_player/target_hero now filled in; destroy the hero.
        if game.target_player is None or game.target_hero is None:
            # Guard: if no opponent has a hero in their party, the ability can't
            # do anything — skip the prompt entirely so the game doesn't softlock.
            no_targets = not any(
                any(isinstance(c, Hero) for c in p.party)
                for p in game.players if p is not player
            )
            if no_targets:
                game.pending_choice = None
                return
            game.pending_choice = ChoiceType.CHOOSE_HERO_FROM_OPPONENT_PARTY
            game.phase = Phase.AWAITING_CHOICE
            return
        target_hero = game.target_hero
        game.target_player.remove_from_party(target_hero)
        game.discard_pile.append(target_hero)
        game.target_player = None   # clear the scratchpad for the next ability
        game.target_hero = None
        game.pending_choice = None  # signal "done" so submit_choice finalizes