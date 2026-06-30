from game_logic.cards.registry import register
from game_logic.base import Hero, HeroClass, RollThreshold, RollCondition
from game_logic.game import Game, Phase, ChoiceType
from game_logic.player import Player
@register("qi_bear")
class QiBear(Hero):
    def __init__(self):
        super().__init__(
            card_id         = "qi_bear",
            name            = "Qi Bear",
            description     = "DISCARD up to 3 cards. For each card discarded, DESTROY a Hero card. ",
            hero_class      = HeroClass.FIGHTER,
            activation_roll = RollThreshold(10, RollCondition.AT_LEAST),
        )

    def use_ability(self, game: Game, player: Player) -> None:
        # "Discard up to 3, destroy a hero per discard." Modelled as N rounds,
        # each round being a (discard one of mine, destroy one of theirs) pair.
        if not player.hand:
            return

        # 1st call: ask HOW MANY pairs to do (0–3). Stored in game.choice and
        # used below as a countdown.
        if game.pending_choice is None:
            game.pending_choice = ChoiceType.CHOOSE_NUMBER
            game.phase = Phase.AWAITING_CHOICE
            return

        # Each loop turn needs two answers (a card to discard, then a hero to
        # destroy). We pause for whichever is still missing, then resume here on
        # the next call — the while loop picks up exactly where it left off.
        while game.choice and game.choice > 0 and player.hand:
            if game.target_card is None:
                game.pending_choice = ChoiceType.CHOOSE_CARD_FROM_OWN_HAND
                game.phase = Phase.AWAITING_CHOICE
                return
            if game.target_hero is None:
                game.pending_choice = ChoiceType.CHOOSE_HERO_FROM_OPPONENT_PARTY
                game.phase = Phase.AWAITING_CHOICE
                return
            # Both answers in: complete one pair and decrement the counter.
            player.discard(game.target_card)
            game.target_player.remove_from_party(game.target_hero)
            game.discard_pile.append(game.target_hero)
            game.target_card = None
            game.target_hero = None
            game.target_player = None
            game.choice -= 1

        game.choice = None
        game.pending_choice = None