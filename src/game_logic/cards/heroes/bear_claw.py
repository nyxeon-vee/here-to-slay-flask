from game_logic.cards.registry import register
from game_logic.base import Hero, HeroClass, RollThreshold, RollCondition
from game_logic.game import Game, Phase, ChoiceType
from game_logic.player import Player
import random
@register("bear_claw")
class BearClaw(Hero):
    def __init__(self):
        super().__init__(
            card_id         = "bear_claw",
            name            = "Bear Claw",
            description     = "Pull a card from another player's hand. If it is a Hero card, pull a second card from that player's hand.",
            hero_class      = HeroClass.FIGHTER,
            activation_roll = RollThreshold(7, RollCondition.AT_LEAST),
        )

    def use_ability(self, game: Game, player: Player) -> None:
        # 1st call: ask which opponent to steal from.
        if game.target_player is None:
            # Guard: if every opponent's hand is empty there's nothing to steal.
            if not any(p.hand for p in game.players if p is not player):
                game.pending_choice = None
                return
            game.pending_choice = ChoiceType.CHOOSE_TARGET_PLAYER
            game.phase = Phase.AWAITING_CHOICE
            return

        # 2nd call: a target is chosen. Guard against an empty hand (the player
        # might have chosen someone who had cards when the prompt opened but
        # discarded since — or the UI allowed picking anyone).
        if not game.target_player.hand:
            game.target_player = None
            game.pending_choice = None
            return

        # Pull a random card from their hand...
        first_card = random.choice(game.target_player.hand)
        game.target_player.hand.remove(first_card)
        player.hand.append(first_card)

        # ...and if it was a Hero, pull a second random card too.
        if isinstance(first_card, Hero) and game.target_player.hand:
            second_card = random.choice(game.target_player.hand)
            game.target_player.hand.remove(second_card)
            player.hand.append(second_card)

        game.target_player = None
        game.pending_choice = None  # signal "done" so submit_choice finalizes