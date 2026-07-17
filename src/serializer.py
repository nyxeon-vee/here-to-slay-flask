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
from game_logic.base import Phase


def _action_context(game: Game) -> dict | None:
    """Describe what is currently happening on the table.

    Returns a dict the client renders in the floating action overlay, or None
    when there's nothing interesting to display (plain ACTION phase).
    """
    phase = game.phase

    # Card on the table waiting for a challenge or still in the challenge window.
    if phase == Phase.CHALLENGE_WINDOW and game.pending_card and game.pending_player:
        pp = game.pending_player
        return {
            "phase":       "challenge_window",
            "player_name": pp.name,
            "player_id":   pp.player_id,
            "card":        game.pending_card.to_dict(),
            "label":       f"played {game.pending_card.name}",
            # Pre-populate dice columns at zero — fills in once a challenge starts.
            "challenger_roll": None,
            "challenged_roll": {"player_id": pp.player_id, "name": pp.name, "roll": None},
        }

    # A roll just happened (hero ability, monster attack, or challenge roll).
    if phase == Phase.ROLL_PENDING:
        ctx = game.pending_roll_context
        if ctx:
            t = ctx["type"]
            if t in ("hero_play", "hero_party"):
                hero   = ctx["hero"]
                player = ctx["player"]
                return {
                    "phase":       "hero_roll",
                    "player_name": player.name,
                    "player_id":   player.player_id,
                    "card":        hero.to_dict() if hero else None,
                    "label":       "using ability" if t == "hero_party" else "playing hero",
                }
            if t == "monster_attack":
                monster = ctx["monster"]
                player  = ctx["player"]
                return {
                    "phase":       "monster_attack",
                    "player_name": player.name,
                    "player_id":   player.player_id,
                    "card":        monster.to_dict(),
                    "label":       "attacking monster",
                }
        # Challenge roll — show both the card being contested and who is rolling.
        if game.challenge_context:
            ctx         = game.challenge_context
            roller      = ctx.get("current_roller")
            challenger  = ctx["challenger"]
            challenged  = ctx["challenged"]
            is_step2    = roller is challenged  # both have rolled
            return {
                "phase":       "challenge_roll",
                "player_name": roller.name if roller else "?",
                "player_id":   roller.player_id if roller else None,
                "card":        game.pending_card.to_dict() if game.pending_card else None,
                "label":       "rolling for challenge",
                # Both rolls shown side-by-side; challenged_roll is None until step 2.
                "challenger_roll": {
                    "player_id": challenger.player_id,
                    "name":      challenger.name,
                    "roll":      ctx.get("challenger_roll") if is_step2 else game.last_roll_current,
                },
                # challenged_roll always present; roll=None until step 2 (shows "?").
                "challenged_roll": {
                    "player_id": challenged.player_id,
                    "name":      challenged.name,
                    "roll":      game.last_roll_current if is_step2 else None,
                },
            }

    # A card effect is paused waiting for player input — keep the card visible.
    if phase == Phase.AWAITING_CHOICE and game.paused:
        card   = game.paused["card"]
        player = game.paused["player"]
        return {
            "phase":       "awaiting_choice",
            "player_name": player.name,
            "player_id":   player.player_id,
            "card":        card.to_dict(),
            "label":       "resolving ability",
        }

    return None


def serialize_player(player: Player, reveal_hand: bool) -> dict:
    return {
        "player_id":     player.player_id,
        "name":          player.name,
        "action_points": player.action_points,
        "current_roll":  player.current_roll,
        # Calming Voice / Mighty Blade: the UI greys this party out during
        # steal / destroy prompts and shows a badge.
        "steal_protected":   player.steal_protected,
        "destroy_protected": player.destroy_protected,
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

        # ── Roll overlay: initial dice value before any modifiers ────────────
        "last_roll": {
            "player_id": game.last_roll_player_id,
            "initial":   game.last_roll_initial,
            "current":   game.last_roll_current,
        } if game.last_roll_player_id else None,

        # ── Action context: what is currently happening on the table ─────────
        # Shown in the floating overlays so players always know what they're
        # responding to — card name, description, and who triggered it.
        "action_context": _action_context(game),

        # ── Prompt info: present only while phase == AWAITING_CHOICE ──────────
        "pending_choice":    game.pending_choice.name if game.pending_choice else None,
        "choice_player_id":  answering,                       # who should answer
        "choice_message":    game.message,                    # optional prompt text set by the card
        # A temporary pool to choose from (Beary Wise, Call To The Fallen, ...).
        "collected_cards":   [c.to_dict() for c in game.collected_cards],

        # ── Event log: public play-by-play for the "chat" panel ──────────────
        "log":               game.event_log,
    }
