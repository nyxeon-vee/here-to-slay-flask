from game_logic.cards.registry import register
from game_logic.base import Hero, Item, GameEvent
from game_logic.game import Game
from game_logic.player import Player


@register("decoy_doll")
class DecoyDoll(Item):
    def __init__(self):
        super().__init__(
            card_id     = "decoy_doll",
            name        = "Decoy Doll",
            description = "If the equipped Hero card would be sacrificed or destroyed, move Decoy Doll to the discard pile instead.",
            is_cursed   = False,
        )

    # Fired by destroy_hero / sacrifice_hero BEFORE the hero is removed.
    # Returning True intercepts: the doll goes to the discard pile, the hero stays.
    def on_event(self, event: GameEvent, game: Game, player: Player) -> bool | None:
        if event not in (GameEvent.HERO_DESTROYED, GameEvent.HERO_SACRIFICED):
            return None
        # Find the hero we're equipped to (items hold no back-reference).
        hero = next((c for c in player.party if isinstance(c, Hero) and c.item is self), None)
        if hero is None:
            return None  # shouldn't happen — fall through to normal destruction
        hero.remove_item()   # fires on_unequip and clears the owner backref
        game.discard_pile.append(self)
        game.log_event(f"{self.name} takes the hit — {hero.name} survives!", "good")
        return True
