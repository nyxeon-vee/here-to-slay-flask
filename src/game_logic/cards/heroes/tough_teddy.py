from game_logic.cards.registry import register
from game_logic.base import Hero, HeroClass, RollThreshold, RollCondition, ChoiceType
from game_logic.game import Game, Phase
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

    def use_ability(self, game: Game, player: Player) -> None:
        if game.pending_choice is None:
            game.pending_targets = [
                p for p in game.players
                if p is not player
                and any(isinstance(c, Hero) and c.hero_class == HeroClass.FIGHTER for c in p.party)
                and p.hand
            ]
            game.pending_choice = ChoiceType.CHOOSE_CARD_FROM_OWN_HAND

        # Process previous player's choice
        if game.target_card is not None and game.pending_targets:
            done_player = game.pending_targets.pop(0)
            done_player.discard(game.target_card)
            game.discard_pile.append(game.target_card)
            game.target_card = None
            game.pending_choice_player = None

        # Ask the next player in queue
        if game.pending_targets:
            game.pending_choice_player = game.pending_targets[0]
            game.phase = Phase.AWAITING_CHOICE
            return

        game.pending_choice = None
