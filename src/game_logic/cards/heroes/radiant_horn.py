from game_logic.base import Hero, HeroClass, RollThreshold, RollCondition, Modifier, ChoiceType
from game_logic.cards.registry import register
from game_logic.game import Game
from game_logic.player import Player


@register("radiant_horn")
class RadiantHorn(Hero):
    def __init__(self) -> None:
        super().__init__(
            card_id         = "radiant_horn",
            name            = "Radiant Horn",
            description     = "Search the discard pile for a Modifier card and add it to your hand.",
            hero_class      = HeroClass.GUARDIAN,
            activation_roll = RollThreshold(6, RollCondition.AT_LEAST),
        )
    def use_ability(self, game: Game, player: Player):
        pool = []
        for card in game.discard_pile:
            if isinstance(card, Modifier):
                pool.append(card)
        if not pool:
            game.log_event("There were no modifiers in the discard pile!")
            return
        game.collected_cards = pool
        game.message = "Choose a modifier from discard pile to add to your hand!"
        chosen_card = yield ChoiceType.CHOOSE_CARD_FROM_POOL
        # Guard: only accept a card that is really still in the discard pile —
        # a stale/forged uid would otherwise crash the generator mid-flight.
        if chosen_card in game.discard_pile:
            game.discard_pile.remove(chosen_card)
            player.hand.append(chosen_card)
            game.log_event(f"{player.name} retrieved {chosen_card.name} from the discard pile")
        game.collected_cards = []

