from game_logic.cards.registry import register
from game_logic.base import Hero, HeroClass, RollThreshold, RollCondition
from game_logic.game import Game, Phase, ChoiceType
from game_logic.player import Player
import random

@register("lucky_bucky")
class LuckyBucky(Hero):
    def __init__(self):
        super().__init__(
            card_id         = "lucky_bucky",
            name            = "Lucky Bucky",
            description     = "Pull a card from another player's hand. If that card is a Hero card, you may play it immediately.",
            hero_class      = HeroClass.BARD,
            activation_roll = RollThreshold(8, RollCondition.AT_LEAST),
        )

    def use_ability(self, game: Game, player: Player) -> None:
        # 1st call: ask which player to steal from.
        if game.target_player is None:
            game.pending_choice = ChoiceType.CHOOSE_TARGET_PLAYER
            game.phase = Phase.AWAITING_CHOICE
            return

        # 2nd call: target is chosen — pull a random card from their hand.
        if not game.collected_cards:
            if not game.target_player.hand:
                game.target_player = None
                return
            pulled = random.choice(game.target_player.hand)
            game.target_player.discard(pulled)

            if not isinstance(pulled, Hero):
                # Not a hero — just take it, done.
                player.hand.append(pulled)
                game.target_player = None
                return

            # Is a hero — ask if the player wants to play it immediately.
            game.collected_cards = [pulled]
            game.pending_choice = ChoiceType.CHOOSE_YES_NO
            game.phase = Phase.AWAITING_CHOICE
            return

        # 3rd call: player answered yes/no. Clear the scratchpad BEFORE calling
        # _execute_card — it runs another Hero.apply() which reuses the same
        # game.target_*/pending_choice fields (same reason as Fuzzy Cheeks).
        pulled = game.collected_cards[0]
        game.collected_cards = []
        game.target_player = None
        game.pending_choice = None
        game.choice, answered_yes = None, game.choice == 0

        if answered_yes:
            game._execute_card(player, pulled)  # play the hero immediately
        else:
            player.hand.append(pulled)  # just take it into hand
