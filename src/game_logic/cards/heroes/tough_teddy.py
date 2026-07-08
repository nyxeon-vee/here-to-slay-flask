from game_logic.cards.registry import register
from game_logic.base import Hero, HeroClass, RollThreshold, RollCondition, ChoiceType
from game_logic.game import Game
from game_logic.player import Player

@register("tough_teddy")
class ToughTeddy(Hero):
    def __init__(self):
        super().__init__(
            card_id         = "tough_teddy",
            name            = "Tough Teddy",
            description     = "Each other player with a Fighter in their Party must DISCARD a card.",
            hero_class      = HeroClass.FIGHTER,
            activation_roll = RollThreshold(4, RollCondition.AT_LEAST),
        )

    def use_ability(self, game: Game, player: Player):
        targets = [
            p for p in game.players
            if p is not player
            and any(isinstance(c, Hero) and c.hero_class == HeroClass.FIGHTER for c in p.party)
            and p.hand
        ]
        if not targets:
            return

        for opp in targets:
            game.pending_choice_player = opp
            game.message = "Choose a card to discard"
            card = yield ChoiceType.CHOOSE_CARD_FROM_OWN_HAND
            opp.discard(card)
            game.discard_pile.append(card)

        game.pending_choice_player = None
        game.message = None
