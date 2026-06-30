from game_logic.cards.registry import register
from game_logic.base import Hero, HeroClass, RollThreshold, RollCondition, Challenge
from game_logic.game import Game, Phase, ChoiceType
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

    def use_ability(self, game: Game, player: Player) -> None:
        # Up to three entries: draw -> (maybe) reveal yes/no -> (maybe) destroy.
        # 1st call: draw 2. If neither is a Challenge, the bonus can't happen, so
        # we're simply done (no AWAITING_CHOICE, ability ends here).
        if game.pending_choice is None:
            player.draw(game.deck)
            player.draw(game.deck)
            drawn = player.hand[-2:]
            if not any(isinstance(c, Challenge) for c in drawn):
                return
            game.pending_choice = ChoiceType.CHOOSE_YES_NO
            game.phase = Phase.AWAITING_CHOICE
            return

        # 2nd call: player answered yes/no to "reveal and destroy a hero?".
        if game.pending_choice == ChoiceType.CHOOSE_YES_NO:
            if game.choice != 0:  # chose "no" -> stop, keep the cards
                game.choice = None
                game.pending_choice = None
                return
            # Chose "yes": switch the open prompt to picking the hero to destroy.
            game.choice = None
            # Guard: even if the player said yes, there might be no opponent
            # heroes to target — skip the prompt so the game doesn't softlock.
            if not any(
                any(isinstance(c, Hero) for c in p.party)
                for p in game.players if p is not player
            ):
                game.pending_choice = None
                return
            game.pending_choice = ChoiceType.CHOOSE_HERO_FROM_OPPONENT_PARTY
            if game.target_player is None or game.target_hero is None:
                game.phase = Phase.AWAITING_CHOICE
                return
        # 3rd call: a hero is targeted -> destroy it.
        target_hero = game.target_hero
        game.target_player.remove_from_party(target_hero)
        game.discard_pile.append(target_hero)
        game.target_player = None
        game.target_hero = None
        game.pending_choice = None