"""
session.py — server-side state that ISN'T game rules but is needed to run a
networked match: which sockets sit at which table, which Player each socket
controls, and one Game per room.

Held in module-level dicts, which is fine for a single-process dev server. For a
real multi-process deployment you'd move this into Redis (and you couldn't keep
live Game objects in memory across workers).
"""
import importlib
import pkgutil

from game_logic.game import Game
from game_logic.player import Player
from game_logic.base import Card, CardType, Leader, Monster
from game_logic.cards.registry import CARD_REGISTRY
import game_logic.cards as cards_pkg


# How many copies of each card type go into the deck. Modifiers and Challenges
# are generic utility cards so we need several copies; named cards (heroes,
# magic, items) are unique so one copy each.
COPIES_BY_TYPE: dict[CardType, int] = {
    CardType.HERO:      1,
    CardType.MAGIC:     1,
    CardType.ITEM:      1,
    CardType.MODIFIER:  4,
    CardType.CHALLENGE: 4,
    CardType.LEADER:    1,
    CardType.MONSTER:   1,
}


def load_all_cards() -> None:
    """Import every module under game_logic.cards so each @register decorator
    runs and fills CARD_REGISTRY. Without this the registry is empty, because a
    decorator only fires when its module is imported. Idempotent."""
    for info in pkgutil.walk_packages(cards_pkg.__path__, cards_pkg.__name__ + "."):
        importlib.import_module(info.name)


class Room:
    """One game table: the Game plus the socket<->Player bookkeeping."""

    def __init__(self, room_id: str) -> None:
        self.room_id = room_id
        self.game = Game()
        self.sid_to_player: dict[str, Player] = {}   # socket id -> the Player it controls
        # Bumped every time a timed window (challenge / modifier) opens. A timer
        # captures the token when it starts and only acts if it still matches when
        # it fires — so any newer action that opened a window cancels the old timer.
        self.window_token: int = 0

    def player_for(self, sid: str) -> Player | None:
        return self.sid_to_player.get(sid)


# room_id -> Room, and socket id -> room_id (lets a handler find its room from sid)
rooms: dict[str, Room] = {}
sid_to_room: dict[str, str] = {}


def get_or_create_room(room_id: str) -> Room:
    if room_id not in rooms:
        rooms[room_id] = Room(room_id)
    return rooms[room_id]


def room_for_sid(sid: str) -> Room | None:
    room_id = sid_to_room.get(sid)
    return rooms.get(room_id) if room_id else None


# ── Lookup helpers: translate the ids the client sends back into objects ──────

def find_player(game: Game, player_id: str) -> Player | None:
    return next((p for p in game.players if p.player_id == player_id), None)


def find_card(game: Game, uid: str) -> Card | None:
    """Find a card instance anywhere on the table by its unique uid. The client
    only ever sends uids it was shown, so we search every visible pile."""
    pools: list[list] = [game.deck, game.discard_pile, game.monster_row, game.collected_cards]
    for p in game.players:
        pools.append(p.hand)
        pools.append(p.party)
    for pool in pools:
        for card in pool:
            if card.uid == uid:
                return card
    return None


def build_decks(game: Game) -> None:
    """Stock the game's three decks from every registered card, split by type.
    Heroes/Magic/Modifiers/Challenges go into the main draw deck; Leaders and
    Monsters into their own decks."""
    load_all_cards()
    game.deck.clear()
    game.leader_deck.clear()
    game.monster_deck.clear()

    for card_cls in CARD_REGISTRY.values():
        count = COPIES_BY_TYPE.get(card_cls.card_type, 1)
        for _ in range(count):
            card = card_cls()             # fresh instance each time — never share one object
            if isinstance(card, Leader):
                game.leader_deck.append(card)
            elif isinstance(card, Monster):
                game.monster_deck.append(card)
            else:
                game.deck.append(card)
