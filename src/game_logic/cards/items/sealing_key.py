from game_logic.cards.registry import register
from game_logic.base import Item


@register("sealing_key")
class SealingKey(Item):
    # The whole effect: while equipped, the hero's ability can't be activated.
    # Enforced in Game.use_party_ability; the UI greys the hero out. No hooks,
    # no state — unequipping (Holy Curselifter) un-seals automatically.
    blocks_ability = True

    def __init__(self):
        super().__init__(
            card_id     = "sealing_key",
            name        = "Sealing Key",
            description  = "You cannot use the equipped Hero card's effect.",
            is_cursed   = True,
        )
