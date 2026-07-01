"""
Core domain model: enums, value objects, and the Card class hierarchy.

This module is the bottom of the dependency graph — game.py and every card
imports from here, but it imports nothing from them (the only references to
Game/Player are type hints, kept under TYPE_CHECKING so there's no import cycle).

Two patterns drive almost everything:

  1. Template method (Hero.apply): the base class owns the shared "play a hero"
     routine — move card to party, roll, apply the leader bonus, check the roll.
     Each concrete hero only fills in use_ability(). See Hero.apply below.

  2. Event hooks (on_event): passive abilities on Leaders and Monsters. The Game
     calls card.on_event(GameEvent.X, ...) at the moment X happens; the card
     decides whether it cares. This keeps Game ignorant of individual cards.
"""
from __future__ import annotations
# `from __future__ import annotations` makes every annotation a lazy string, so
# we can hint Game/Player without importing them at runtime (avoids a cycle).
from typing import TYPE_CHECKING, NamedTuple
if TYPE_CHECKING:
    from game_logic.game import Game
    from game_logic.player import Player
from abc import ABC, abstractmethod
from enum import Enum, auto
import uuid

class RollCondition(Enum):
    AT_LEAST = "at_least"
    AT_MOST  = "at_most"

class RollOutcome(Enum):
    WIN  = "win"
    LOSE = "lose"
    DRAW = "draw"

# A roll target, e.g. RollThreshold(8, AT_LEAST) means "roll 8 or higher".
# Immutable value object (NamedTuple) so it can be shared/compared safely.
class RollThreshold(NamedTuple):
    value: int
    condition: RollCondition

    def check(self, roll: int) -> bool:
        """True if `roll` satisfies this threshold."""
        return roll <= self.value if self.condition == RollCondition.AT_MOST else roll >= self.value

# What kind of input a card is waiting on while game.phase == AWAITING_CHOICE.
# The UI layer reads game.pending_choice to know which prompt to show, then
# writes the answer into game.target_*/choice and re-calls the card. See the
# "re-entrant ability" note on Hero.use_ability below.
class ChoiceType(Enum):
    CHOOSE_HERO_FROM_OPPONENT_PARTY = auto()  # answer -> game.target_player + game.target_hero
    CHOOSE_HERO_FROM_OWN_PARTY      = auto()  # answer -> game.target_hero
    CHOOSE_HERO_FROM_ANY_PARTY      = auto()  # anwser -> game.target_hero
    CHOOSE_TARGET_PLAYER            = auto()  # answer -> game.target_player
    CHOOSE_CARD_FROM_OWN_HAND       = auto()  # answer -> game.target_card
    CHOOSE_CARD_FROM_POOL           = auto()  # pick from game.collected_cards -> game.target_card
    CHOOSE_YES_NO                   = auto()  # answer -> game.choice (0 = yes, 1 = no)
    CHOOSE_NUMBER                   = auto()  # answer -> game.choice (an integer)

# Passive-ability triggers. Game fires these at the relevant moment via
# leader/monster.on_event(); a card's on_event checks the event and reacts.
class GameEvent(Enum):
    HERO_ROLL               = auto()  # player rolled to activate a Hero
    MAGIC_PLAYED            = auto()  # player played a Magic card
    CARD_DRAWN              = auto()
    MONSTER_ATTACK          = auto()  # player rolled to slay a Monster
    CHALLENGE_ROLL          = auto()  # player rolled as part of a challenge
    MONSTER_SLAIN           = auto()
    MODIFIER_PLAYED         = auto()  # a Modifier was played on someone's roll
    SUCCESSFUL_HERO_ROLL    = auto()  # a Hero roll succeeded (fires on party monsters)
    UNSUCCESSFUL_HERO_ROLL  = auto()  # a Hero roll unsucceeded (fires on item)
# The single source of truth for "what is the game waiting for right now".
# Every public Game method guards on this, so illegal actions raise instead of
# corrupting state. Rough flow: ACTION -> (play card) -> CHALLENGE_WINDOW ->
# ROLL_PENDING (modifier window) -> back to ACTION, with AWAITING_CHOICE as a
# detour whenever a card needs player input mid-resolution.
class Phase(Enum):
    LOBBY            = auto()  # before start_game()
    ACTION           = auto()  # current player spending action points
    CHALLENGE_WINDOW = auto()  # a played card may be challenged by opponents
    ROLL_PENDING     = auto()  # a roll just happened; modifiers may be played
    AWAITING_CHOICE  = auto()  # a card is paused waiting on player input
    END_TURN         = auto()

class CardType(Enum):
    HERO      = "hero"
    MONSTER   = "monster"
    ITEM      = "item"
    MAGIC     = "magic"
    MODIFIER  = "modifier"
    CHALLENGE = "challenge"
    LEADER    = "leader"

class HeroClass(Enum):
    FIGHTER = "fighter"
    RANGER  = "ranger"
    WIZARD  = "wizard"
    BARD    = "bard"
    THIEF   = "thief"
    GUARDIAN = "guardian"

# Gate for attacking a monster: you need at least `min_heroes` heroes AND every
# class listed in `required_classes` present in your party (the leader counts).
class PartyRequirement(NamedTuple):
    min_heroes: int
    required_classes: tuple[HeroClass, ...]

    def check(self, party: list, leader: Leader) -> bool:
        """True if `party` (plus its `leader`) meets this requirement."""
        hero_count = sum(isinstance(c, Hero) for c in party)
        if hero_count < self.min_heroes:
            return False
        # The leader's class also counts toward the required classes.
        party_classes = {c.hero_class for c in party if isinstance(c, Hero)} | {leader.hero_class}
        return all(cls in party_classes for cls in self.required_classes)
    
class Card(ABC):
    card_type: CardType
    action_cost: int = 1
    def __init__(self, card_id: str, name: str, description: str) -> None:
        self.card_id = card_id          # the card's TYPE (shared by every copy)
        self.uid = uuid.uuid4().hex     # this physical copy's unique id (for targeting)
        self.name = name
        self.description = description
        super().__init__()
        
    @abstractmethod
    def apply(self, game: Game, player: Player) -> None: ...


    def to_dict(self) -> dict:
        return {
            "uid":         self.uid,
            "card_id":     self.card_id,
            "name":        self.name,
            "description": self.description,
            "card_type":   self.card_type.value,
        }

    def __repr__(self):
        return f"<{self.__class__.__name__} id={self.card_id!r}>"
    
class Hero(Card):
    card_type: CardType = CardType.HERO

    def __init__(self, card_id, name, description, hero_class: HeroClass, activation_roll: RollThreshold):
        super().__init__(card_id, name, description)
        self.hero_class = hero_class
        self.activation_roll = activation_roll
        self.item: Item | None = None
        self.was_used_this_turn: bool = False

    def add_item(self, item: Item) -> None:
        self.item = item

    def reset_turn(self) -> None:
        """Called at the start of each new turn to allow the ability again."""
        self.was_used_this_turn = False

    def apply(self, game: Game, player: Player) -> None:
        """Template method: the shared 'play a Hero from hand' sequence.

        Moves the card into the party, then delegates the roll + ability to
        roll_and_activate so the same logic is reused when activating a party hero.
        """
        player.hand.remove(self)
        player.party.append(self)
        self.roll_and_activate(game, player, context_type="hero_play")

    def roll_and_activate(self, game: Game, player: Player, context_type: str = "hero_party") -> None:
        """Roll for this hero and park in ROLL_PENDING for the modifier window.

        Sets `game.pending_roll_context` so game.finish_pending_roll() knows
        how to resume after the modifier window closes. Does NOT run the
        ability — that happens in finish_roll(), called by finish_pending_roll().

          1. roll the dice (stored on player.current_roll + game.last_roll_initial)
          2. let the leader's passive bump the roll (HERO_ROLL event)
          3. store context, leave phase at ROLL_PENDING
        """
        self.was_used_this_turn = True
        game.phase = Phase.ROLL_PENDING
        game.roll_dice(player)
        if player.party_leader:
            player.party_leader.on_event(GameEvent.HERO_ROLL, game, player)
        game.pending_roll_context = {"type": context_type, "hero": self, "player": player}

    def finish_roll(self, game: Game, player: Player) -> None:
        """Resolve this hero's roll after the modifier window has closed.

        Called by game.finish_pending_roll(). WIN fires party-monster events then
        runs the ability; LOSE fires the equipped item's passive.
        """
        if self.evaluate_roll(player.current_roll) == RollOutcome.WIN:
            for party_card in player.party:
                if isinstance(party_card, Monster):
                    party_card.on_event(GameEvent.SUCCESSFUL_HERO_ROLL, game, player)
            self.use_ability(game, player)
        else:
            if self.item is not None:
                self.item.on_event(GameEvent.UNSUCCESSFUL_HERO_ROLL, game, player)

    @abstractmethod
    def use_ability(self, game: Game, player: Player) -> None:
        """This hero's effect, run once its roll succeeds.

        IMPORTANT — abilities are RE-ENTRANT. If an ability needs player input it
        cannot block; instead it:
          - sets game.pending_choice (what kind of answer it needs),
          - sets game.phase = AWAITING_CHOICE, and
          - returns.
        The outer layer collects the answer (into game.target_*/choice) and calls
        use_ability AGAIN. So an ability that asks N questions is entered N+1
        times, and must read game.pending_choice / game.target_* to figure out
        which step it's resuming. game.pending_choice is None on the first entry.
        """
        ...

    def evaluate_roll(self, roll: int) -> RollOutcome:
        return RollOutcome.WIN if self.activation_roll.check(roll) else RollOutcome.LOSE

    def to_dict(self):
        return {
            **super().to_dict(),
            "hero_class":         self.hero_class.value,
            "activation_roll":    {"value": self.activation_roll.value, "condition": self.activation_roll.condition.value},
            "item":               self.item.to_dict() if self.item else None,
            "was_used_this_turn": self.was_used_this_turn,
        }
class Monster(Card):
    card_type: CardType = CardType.MONSTER
    # defeat/fail are the two roll bands (see evaluate_roll); party_requirement
    # gates who may attack it; fail_description is UI text for the fail penalty
    # (defaults to "" so simple/stub monsters can omit it).
    def __init__(self, card_id: str, name: str, description: str, defeat: RollThreshold, fail: RollThreshold, party_requirement: PartyRequirement, fail_description: str = "") -> None:
        super().__init__(card_id, name, description)
        self.defeat = defeat
        self.fail = fail
        self.party_requirement = party_requirement
        self.fail_description = fail_description
    @abstractmethod
    def apply_failure(self, game: Game, player: Player) -> None:
        """Penalty when a slay attempt rolls in the 'fail' band.

        Re-entrant just like Hero.use_ability — most monsters make you sacrifice
        a hero, which needs a CHOOSE_HERO_FROM_OWN_PARTY prompt, so this method
        is entered again after the player picks. (fail_description is the
        human-readable version of this penalty for the UI.)
        """

    def apply(self, game: Game, player: Player) -> None:
        # Monsters aren't "played" from hand — they're slain via attack_monster —
        # so Card.apply is a no-op here, present only to satisfy the ABC.
        pass

    def on_event(self, event: GameEvent, game: Game, player: Player) -> None:
        # Default: ignore all events. Monsters with passives (Anuran Cauldron,
        # Abyss Queen, ...) override this. Non-no-op so Game can call it blindly.
        pass

    def evaluate_roll(self, roll: int) -> RollOutcome:
        # A slay roll has three bands: high -> WIN (slain), low -> LOSE (penalty),
        # in between -> DRAW (nothing happens, monster stays).
        if self.defeat.check(roll):
            return RollOutcome.WIN
        if self.fail.check(roll):
            return RollOutcome.LOSE
        return RollOutcome.DRAW

    def to_dict(self):
        return {
            **super().to_dict(),
            "defeat": {"value": self.defeat.value, "condition": self.defeat.condition.value},
            "fail":   {"value": self.fail.value,   "condition": self.fail.condition.value},
        }

class Item(Card):
    card_type: CardType = CardType.ITEM
    def __init__(self, card_id: str, name: str, description: str, is_cursed: bool = False,) -> None:
        super().__init__(card_id, name, description)
        self.is_cursed = is_cursed

    def on_event(self, event: GameEvent, game: Game, player: Player) -> None:
        # Default: ignore events. An item equipped to a hero (e.g. Particularly
        # Rusty Coin) overrides this to react to that hero's rolls. No-op so
        # Hero.apply can call self.item.on_event blindly.
        pass

    def to_dict(self):
        return {
            **super().to_dict(),
            "is_cursed": self.is_cursed,
        }
    
class Magic(Card):
    card_type: CardType = CardType.MAGIC
    def __init__(self, card_id: str, name: str, description: str,) -> None:
        super().__init__(card_id, name, description)
    
class Modifier(Card):
    card_type: CardType = CardType.MODIFIER

    def __init__(self, card_id: str, name: str, description: str, options: tuple[int, ...]) -> None:
        super().__init__(card_id, name, description)
        self.options = options

    @property
    def has_choice(self) -> bool:
        return len(self.options) > 1

    def to_dict(self):
        return {
            **super().to_dict(),
            "options": list(self.options),
        }

class Challenge(Card):
    card_type: CardType = CardType.CHALLENGE
    def __init__(self, card_id: str, name: str, description: str) -> None:
        super().__init__(card_id, name, description)

class Leader(Card):
    card_type: CardType = CardType.LEADER
    def __init__(self, card_id: str, name: str, description: str, hero_class: HeroClass) -> None:
        super().__init__(card_id, name, description)
        self.hero_class = hero_class
    def to_dict(self):
        return {
            **super().to_dict(),
            "hero_class": self.hero_class.value,   # .value — the enum itself isn't JSON serializable
        }
    def apply(self, game: Game, player: Player) -> None:
        # Leaders are assigned at game start, never played from hand — no-op.
        pass

    def on_event(self, event: GameEvent, game: Game, player: Player) -> None:
        # Default: no passive. Each concrete leader overrides this to react to a
        # single GameEvent (e.g. The Charismatic Song adds +1 on HERO_ROLL).
        pass