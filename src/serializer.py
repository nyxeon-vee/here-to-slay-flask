"""
serializer.py — turn Game/Player objects into plain dicts the client can render.

The socket layer ships these as JSON. Two rules shape what goes in:

  * Hands are SECRET. A player sees their own hand cards but only the COUNT of
    everyone else's. So `serialize_game` takes a `viewer` and hands are revealed
    only for that viewer — which is why each socket gets its OWN payload.
  * Everything the UI needs to render the board AND to build its next move lives
    here: phase, whose turn it is, the open prompt (pending_choice) and who must
    answer it. Cards carry a `uid` (see Card.to_dict) so the client can point at
    one specific card when answering.
"""
from game_logic.game import Game
from game_logic.player import Player


def serialize_player(player: Player, reveal_hand: bool) -> dict:
    return {
        "player_id":     player.player_id,
        "name":          player.name,
        "action_points": player.action_points,
        "current_roll":  player.current_roll,
        "party":         [c.to_dict() for c in player.party],
        "party_leader":  player.party_leader.to_dict() if player.party_leader else None,
        "hand_count":    len(player.hand),
        # Only the owner gets real hand cards; everyone else gets None and renders
        # `hand_count` face-down cards instead.
        "hand":          [c.to_dict() for c in player.hand] if reveal_hand else None,
    }


def serialize_game(game: Game, viewer: Player) -> dict:
    # Who is expected to answer an open prompt? Multi-player effects set
    # pending_choice_player explicitly (an opponent must discard); for ordinary
    # effects it's just the current player. None when no prompt is open.
    answering = None
    if game.pending_choice is not None:
        answerer = game.pending_choice_player or game.current_player
        answering = answerer.player_id if answerer else None

    return {
        "phase":             game.phase.name,
        "current_player_id": game.current_player.player_id if game.current_player else None,
        "monster_row":       [m.to_dict() for m in game.monster_row],
        "discard_top":       game.discard_pile[-1].to_dict() if game.discard_pile else None,
        "deck_count":        len(game.deck),
        # One entry per player; the viewer's own hand is the only one revealed.
        "players":           [serialize_player(p, reveal_hand=(p is viewer)) for p in game.players],

        # ── The card "on the table" during CHALLENGE_WINDOW ──────────────────
        # What was just played and by whom, so opponents can decide to challenge.
        "pending_card":      game.pending_card.to_dict() if game.pending_card else None,
        "pending_player_id": game.pending_player.player_id if game.pending_player else None,

        # ── Prompt info: present only while phase == AWAITING_CHOICE ──────────
        "pending_choice":    game.pending_choice.name if game.pending_choice else None,
        "choice_player_id":  answering,                       # who should answer
        # A temporary pool to choose from (Beary Wise, Call To The Fallen, ...).
        "collected_cards":   [c.to_dict() for c in game.collected_cards],
    }
