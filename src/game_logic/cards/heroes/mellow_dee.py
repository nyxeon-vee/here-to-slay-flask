from game_logic.cards.registry import register
from game_logic.base import Hero, HeroClass, RollThreshold, RollCondition, Challenge
from game_logic.game import Game, Phase, ChoiceType
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

    def use_ability(self, game: Game, player: Player) -> None:
        # 1st call: draw a card.
        if game.pending_choice is None:
            if not game.deck:
                return  # deck empty — fizzle cleanly
            drawn = game.deck.pop()
            if not isinstance(drawn, Hero):
                # Non-hero: just take it into hand, done.
                player.hand.append(drawn)
                return
            # Hero drawn — ask whether to play it immediately.
            game.target_card = drawn
            game.pending_choice = ChoiceType.CHOOSE_YES_NO
            game.phase = Phase.AWAITING_CHOICE
            game.message = "Do you want to play the drawn hero card?"
            return

        # 2nd call: player answered. Clear scratchpad BEFORE _execute_card so the
        # nested Hero.apply() gets a clean game.target_* / pending_choice state.
        drawn = game.target_card
        game.target_card = None
        if drawn is None:
            return
        game.pending_choice = None
        game.message = None
        answered_yes = game.choice == 0  # CHOOSE_YES_NO: 0 = Yes, 1 = No
        game.choice = None

        if answered_yes:
            game._execute_card(player, drawn)
        else:
            player.hand.append(drawn)  # declined — take it into hand