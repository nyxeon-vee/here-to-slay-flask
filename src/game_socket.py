"""
game_socket.py — the translation layer between WebSocket events and the Game.

Every handler follows the same shape:

    1. look up the room / player / card from the socket and the event payload
    2. call ONE Game method inside try/except
    3. on a rule violation -> emit "error" to just that socket
    4. on success         -> broadcast fresh state to everyone in the room

The Game holds all the rules; this file only routes messages, serializes state,
and runs the WALL-CLOCK TIMERS that close the challenge / modifier windows (the
Game is deliberately ignorant of real time).

Timed windows
-------------
Playing a card no longer resolves it immediately — it opens a CHALLENGE_WINDOW.
A background timer waits a few seconds:
  * nobody challenged  -> the card resolves (resolve_pending_card).
  * someone challenges -> the challenge rolls run, each behind its own modifier
    window (also timed) so players can play modifiers before each roll counts.
Any action that moves the state forward bumps room.window_token, which makes the
previously-scheduled timer a no-op when it fires (see _open_timed_window).

Client -> server events:  join_game, start_game, play_card, draw_card, end_turn,
    discard_all, attack_monster, use_party_ability, play_modifier, play_challenge,
    submit_choice
Server -> client events:  game_state (personalized per socket), error
"""
from flask import request
from flask_socketio import SocketIO, join_room, emit

from game_logic.base import Phase
from game_logic.exceptions import (
    InvalidPhaseError,
    CardNotInHandError,
    CardNotInPartyError,
    PlayerNotEnoughActionPointsError,
    PartyNotFulfillRequiermentError,
)
from serializer import serialize_game
import session

# How long each window stays open (seconds). Tune for your group — short for dev.
CHALLENGE_WINDOW_SECONDS = 8   # time for opponents to play a Challenge
MODIFIER_WINDOW_SECONDS = 6    # time to play Modifiers before a roll is locked in

# Game-rule exceptions we translate into a friendly "error" event instead of a
# 500. Anything NOT in here is a real bug and should crash loudly in dev.
RULE_ERRORS = (
    InvalidPhaseError,
    CardNotInHandError,
    CardNotInPartyError,
    PlayerNotEnoughActionPointsError,
    PartyNotFulfillRequiermentError,
    ValueError,            # play_modifier raises this for a bad choice index
)


# ── State broadcasting ───────────────────────────────────────────────────────

def _broadcast_state(room: "session.Room", socketio: SocketIO) -> None:
    """Send each socket its OWN view of the game (hands differ per player). Uses
    socketio.emit so it works from background timers too, not just handlers."""
    for sid, player in room.sid_to_player.items():
        socketio.emit("game_state", serialize_game(room.game, player), to=sid)


def _error(message: str) -> None:
    """Send an error only to the socket that triggered the current event."""
    emit("error", {"message": message}, to=request.sid)


def _do(room, socketio, action) -> bool:
    """Run a Game call, relay rule errors, broadcast on success. Returns whether
    it succeeded so the caller can decide to open a follow-up window."""
    if room is None:
        _error("You are not in a room")
        return False
    try:
        action()
    except RULE_ERRORS as e:
        _error(str(e) or e.__class__.__name__)
        return False
    _broadcast_state(room, socketio)
    return True


# ── Timed windows ────────────────────────────────────────────────────────────

def _open_timed_window(room: "session.Room", socketio: SocketIO) -> None:
    """If the game is sitting in a timed phase, start (or restart) its timer.

    Bumping window_token first invalidates any timer already in flight — this is
    how playing a challenge/modifier 'cancels' the previous countdown and how a
    new modifier 'resets' the clock. When the timer fires it only acts if its
    captured token is still current.
    """
    game = room.game
    if game.phase == Phase.CHALLENGE_WINDOW:
        seconds = CHALLENGE_WINDOW_SECONDS
    elif game.phase == Phase.ROLL_PENDING and game.challenge_context:
        seconds = MODIFIER_WINDOW_SECONDS
    else:
        return  # ACTION / AWAITING_CHOICE / etc. — nothing to time

    room.window_token += 1
    token = room.window_token

    def timer():
        socketio.sleep(seconds)
        if room.window_token == token:        # still the current window?
            _advance_window(room, socketio)

    socketio.start_background_task(timer)


def _advance_window(room: "session.Room", socketio: SocketIO) -> None:
    """A timed window expired with no further action — move the state forward by
    one step, open the next window if the new state is also timed, broadcast."""
    game = room.game
    if game.phase == Phase.CHALLENGE_WINDOW:
        game.resolve_pending_card()                       # no challenge came -> resolve
    elif game.phase == Phase.ROLL_PENDING and game.challenge_context:
        ctx = game.challenge_context
        if ctx["current_roller"] is ctx["challenger"]:
            game.close_challenge_roll_1()                 # challenged player rolls next
        else:
            game.close_challenge_roll_2()                 # compare the rolls & resolve
    _open_timed_window(room, socketio)                    # next window, if any
    _broadcast_state(room, socketio)


def register_handlers(socketio: SocketIO) -> None:
    """Attach every @socketio.on handler. Called once from app.py."""

    # ── Connection lifecycle ────────────────────────────────────────────────

    @socketio.on("disconnect")
    def on_disconnect():
        room = session.room_for_sid(request.sid)
        if room:
            room.sid_to_player.pop(request.sid, None)
        session.sid_to_room.pop(request.sid, None)

    @socketio.on("join_game")
    def on_join(data):
        # data: { room_id, name }. The socket id doubles as the player_id.
        room = session.get_or_create_room(data["room_id"])
        player = session.Player(player_id=request.sid, name=data.get("name", "Anon"))
        room.game.add_player(player)
        room.sid_to_player[request.sid] = player
        session.sid_to_room[request.sid] = room.room_id
        join_room(room.room_id)
        _broadcast_state(room, socketio)

    @socketio.on("start_game")
    def on_start(_data=None):
        room, _player = _ctx()
        if not room:
            return _error("You are not in a room")
        try:
            session.build_decks(room.game)
            room.game.start_game()
        except RULE_ERRORS as e:
            return _error(str(e))
        _broadcast_state(room, socketio)

    # ── Turn actions ────────────────────────────────────────────────────────

    @socketio.on("play_card")
    def on_play_card(data):
        room, player = _ctx()
        if not room:
            return _error("You are not in a room")
        card = session.find_card(room.game, data["uid"])
        # On success the card is committed and CHALLENGE_WINDOW is open — start
        # the timer that resolves it if nobody challenges.
        if _do(room, socketio, lambda: room.game.play_card(player, card)):
            _open_timed_window(room, socketio)

    @socketio.on("draw_card")
    def on_draw(_data=None):
        room, player = _ctx()
        _do(room, socketio, lambda: room.game.draw_card(player))

    @socketio.on("end_turn")
    def on_end_turn(_data=None):
        room, player = _ctx()
        _do(room, socketio, lambda: room.game.end_turn(player))

    @socketio.on("discard_all")
    def on_discard_all(_data=None):
        room, player = _ctx()
        _do(room, socketio, lambda: room.game.discard_all_cards(player))

    @socketio.on("attack_monster")
    def on_attack(data):
        room, player = _ctx()
        if not room:
            return _error("You are not in a room")
        monster = session.find_card(room.game, data["uid"])
        _do(room, socketio, lambda: room.game.attack_monster(player, monster))

    @socketio.on("use_party_ability")
    def on_use_party(data):
        room, player = _ctx()
        if not room:
            return _error("You are not in a room")
        hero = session.find_card(room.game, data["uid"])
        _do(room, socketio, lambda: room.game.use_party_ability(player, hero))

    @socketio.on("play_modifier")
    def on_play_modifier(data):
        # data: { uid, choice }. Playing a modifier RESETS the roll's window so
        # others can respond — _open_timed_window restarts the clock.
        room, player = _ctx()
        if not room:
            return _error("You are not in a room")
        card = session.find_card(room.game, data["uid"])
        if _do(room, socketio, lambda: room.game.play_modifier(player, card, data.get("choice", 0))):
            _open_timed_window(room, socketio)

    @socketio.on("play_challenge")
    def on_play_challenge(data):
        # Challenging cancels the challenge-window timer (the token bump inside
        # _open_timed_window) and opens the first modifier window for the rolls.
        room, player = _ctx()
        if not room:
            return _error("You are not in a room")
        card = session.find_card(room.game, data["uid"])
        if _do(room, socketio, lambda: room.game.play_challenge(player, card)):
            _open_timed_window(room, socketio)

    # ── Answering a prompt (the re-entrant abilities) ───────────────────────

    @socketio.on("submit_choice")
    def on_submit_choice(data):
        """data carries whatever the open prompt needs:

            CHOOSE_TARGET_PLAYER            -> { target_player_id }
            CHOOSE_HERO_FROM_OPPONENT_PARTY -> { target_player_id, target_hero_uid }
            CHOOSE_HERO_FROM_OWN_PARTY      -> { target_hero_uid }
            CHOOSE_CARD_FROM_OWN_HAND       -> { target_card_uid }
            CHOOSE_CARD_FROM_POOL           -> { target_card_uid }
            CHOOSE_YES_NO                   -> { choice: 0|1 }
            CHOOSE_NUMBER                   -> { choice: int }
        """
        room, player = _ctx()
        if not room:
            return _error("You are not in a room")
        game = room.game
        if game.pending_choice is None:
            return _error("There is nothing to choose right now")

        # Only the player the prompt is aimed at may answer it.
        answerer = game.pending_choice_player or game.current_player
        if player is not answerer:
            return _error("This choice isn't yours to make")

        # Copy the relevant answer fields into the scratchpad; the paused effect
        # reads only what it needs.
        if "target_player_id" in data:
            game.target_player = session.find_player(game, data["target_player_id"])
        if "target_hero_uid" in data:
            game.target_hero = session.find_card(game, data["target_hero_uid"])
        if "target_card_uid" in data:
            game.target_card = session.find_card(game, data["target_card_uid"])
        if "choice" in data:
            game.choice = int(data["choice"])

        _do(room, socketio, game.submit_choice)


# ── Small shared helper ──────────────────────────────────────────────────────

def _ctx():
    """Return (room, player) for the socket firing the current event."""
    room = session.room_for_sid(request.sid)
    player = room.player_for(request.sid) if room else None
    return room, player
