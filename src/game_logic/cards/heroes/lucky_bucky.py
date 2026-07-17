from game_logic.cards.registry import register
from game_logic.base import Hero, HeroClass, RollThreshold, RollCondition, ChoiceType
from game_logic.game import Game
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

    def use_ability(self, game: Game, player: Player):
        if not any(p.hand for p in game.players if p is not player):
            return  # no one has cards — fizzle
        game.message = "Choose a player to steal from"
        target = yield ChoiceType.CHOOSE_TARGET_PLAYER
        if not target.hand:
            game.message = None
            return
        pulled = random.choice(target.hand)
        target.hand.remove(pulled)
        if not isinstance(pulled, Hero):
            player.hand.append(pulled)
            game.message = None
            return
        # Pulled a hero — ask whether to play it immediately.
        # Clear message BEFORE the nested hero would set its own.
        game.message = "Play the stolen hero immediately?"
        play_it = yield ChoiceType.CHOOSE_YES_NO
        game.message = None
        # The card goes to the hand either way — Hero.apply expects to move it
        # from hand to party, so playing it without this step would crash.
        player.hand.append(pulled)
        if play_it:
            game._execute_card(player, pulled)
