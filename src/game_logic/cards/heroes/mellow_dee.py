from game_logic.cards.registry import register
from game_logic.base import Hero, HeroClass, RollThreshold, RollCondition, ChoiceType
from game_logic.game import Game
from game_logic.player import Player

@register("mellow_dee")
class MellowDee(Hero):
    def __init__(self):
        super().__init__(
            card_id         = "mellow_dee",
            name            = "Mellow Dee",
            description     = "DRAW a card. If that card is a Hero card, you may play it immediately. ",
            hero_class      = HeroClass.BARD,
            activation_roll = RollThreshold(7, RollCondition.AT_LEAST),
        )

    def use_ability(self, game: Game, player: Player):
        if not game._refill_deck_if_empty():
            return  # deck AND discard empty — fizzle
        drawn = game.deck.pop()
        if not isinstance(drawn, Hero):
            player.hand.append(drawn)
            return  # non-hero: just take it, done
        game.message = "Play the drawn hero immediately?"
        play_it = yield ChoiceType.CHOOSE_YES_NO
        # Clear message BEFORE _execute_card — the inner hero reuses game.message.
        game.message = None
        # The card goes to the hand either way — Hero.apply expects to move it
        # from hand to party, so playing it without this step would crash.
        player.hand.append(drawn)
        if play_it:
            game._execute_card(player, drawn)
