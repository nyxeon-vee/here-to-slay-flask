/* ──────────────────────────────────────────────────────────────────────────
   game.js — the browser client.

   It does three things:
     1. emits the documented socket events (join_game, play_card, …) on click
     2. listens for "game_state" (a personalized snapshot) and re-renders
     3. makes board elements clickable depending on the current phase / prompt

   The server is the only source of truth — every click just sends an intent and
   the next game_state reflects the result (or an "error" toast if it was illegal).
   See game_socket.py for the event contract.
   ────────────────────────────────────────────────────────────────────────── */

const socket = io();
let STATE = null;       // last game_state snapshot received
let MY_ID = null;       // our player_id == our socket id (set by join_game server-side)

socket.on("connect", () => { MY_ID = socket.id; });
socket.on("game_state", (s) => { STATE = s; render(); });
socket.on("error", (e) => flash(e.message));

// ── Helpers to read the snapshot from "my" point of view ───────────────────
const me        = () => STATE.players.find(p => p.player_id === MY_ID);
const opponents = () => STATE.players.filter(p => p.player_id !== MY_ID);
const isMyTurn  = () => STATE.current_player_id === MY_ID;
// The choice I personally must answer right now (null if none / not mine).
const myChoice  = () =>
  (STATE.pending_choice && STATE.choice_player_id === MY_ID) ? STATE.pending_choice : null;

// ── Emit shortcuts ─────────────────────────────────────────────────────────
const send = (event, data = {}) => socket.emit(event, data);

// ───────────────────────────────────────────────────────────────────────────
//  JOIN / LOBBY / START
// ───────────────────────────────────────────────────────────────────────────
const $ = (id) => document.getElementById(id);

$("join-btn").onclick = () => {
  const room_id = $("room-input").value.trim() || "table1";
  const name = $("name-input").value.trim() || "Player";
  send("join_game", { room_id, name });
};
$("start-btn").onclick = () => send("start_game");

// Wire the always-available turn actions (draw / discard / end turn).
document.querySelectorAll("#action-bar button").forEach(btn => {
  btn.onclick = () => send(btn.dataset.act);
});

// ───────────────────────────────────────────────────────────────────────────
//  TOP-LEVEL RENDER — pick the screen, then fill the board
// ───────────────────────────────────────────────────────────────────────────
function render() {
  if (!STATE) return;

  const joined = !!me();
  const inGame = joined && STATE.phase !== "LOBBY";

  $("join-screen").classList.toggle("hidden", joined);
  $("lobby-screen").classList.toggle("hidden", !(joined && !inGame));
  $("game-screen").classList.toggle("hidden", !inGame);

  if (!inGame) return renderLobby();
  renderTopbar();
  renderRollOverlay();
  renderPrompt();
  renderOpponents();
  renderMonsterRow();
  renderMe();
}

function renderLobby() {
  $("lobby-room").textContent = "";
  const ul = $("lobby-players");
  ul.innerHTML = "";
  STATE.players.forEach(p => {
    const li = document.createElement("li");
    li.textContent = p.name + (p.player_id === MY_ID ? "  (you)" : "");
    ul.appendChild(li);
  });
}

function renderRollOverlay() {
  const overlay = $("roll-overlay");
  const lr = STATE.last_roll;

  if (!lr || STATE.phase !== "ROLL_PENDING") {
    overlay.classList.add("hidden");
    return;
  }

  // Dice faces are fixed to the INITIAL roll (before any modifier is applied).
  // The running total below updates live as modifiers are played.
  const d1 = Math.floor(lr.initial / 2);
  const d2 = lr.initial - d1;

  // Find the roller to get their current (possibly modified) total.
  const roller = STATE.players.find(p => p.player_id === lr.player_id);
  const currentTotal = roller ? roller.current_roll : lr.initial;
  const delta = currentTotal - lr.initial;
  const deltaStr = delta === 0 ? "" : (delta > 0 ? ` (+${delta})` : ` (${delta})`);

  $("roll-who").textContent =
    lr.player_id === MY_ID ? "Your roll" : `${nameOf(lr.player_id)}'s roll`;

  const diceRow = $("roll-dice");
  diceRow.innerHTML = "";
  [d1, d2].forEach(val => {
    const die = document.createElement("div");
    die.className = "die";
    die.textContent = val;
    diceRow.appendChild(die);
  });

  $("roll-total").textContent = `= ${currentTotal}${deltaStr}`;
  overlay.classList.remove("hidden");
}

function renderTopbar() {
  $("phase-pill").textContent = "Phase: " + STATE.phase;
  const turn = $("turn-pill");
  const cur = STATE.players.find(p => p.player_id === STATE.current_player_id);
  turn.textContent = isMyTurn() ? "Your turn" : `Turn: ${cur ? cur.name : "—"}`;
  turn.classList.toggle("turn-mine", isMyTurn());
  $("deck-count").textContent = STATE.deck_count;
  $("discard-top").textContent = STATE.discard_top ? STATE.discard_top.name : "—";
}

// ───────────────────────────────────────────────────────────────────────────
//  CARD ELEMENT BUILDER
//  opts: { selectable, onClick, faceDown, mini }
// ───────────────────────────────────────────────────────────────────────────

// card_type values from the server are singular ("hero", "monster", …).
// The image folder uses plural names to match a conventional asset layout.
const CARD_TYPE_FOLDER = {
  hero: "heroes", monster: "monsters", leader: "leaders",
  item: "items", magic: "magic", modifier: "modifiers", challenge: "challenges",
};

function cardEl(card, opts = {}) {
  const el = document.createElement("div");
  if (opts.faceDown) {
    el.className = "card card--back" + (opts.mini ? " mini" : "");
    return el;
  }

  el.className = "card card--img card--" + card.card_type + (opts.mini ? " mini" : "");
  el.dataset.tooltip = `${card.name}\n${card.description}`;

  const folder = CARD_TYPE_FOLDER[card.card_type] || card.card_type;
  const img = document.createElement("img");
  img.src = `/static/img/card/${folder}/${card.card_id}.png`;
  img.alt = card.name;
  img.className = "card-img";
  // If the image is missing, fall back to a small text label so the card
  // is still usable during development before all art is in place.
  img.onerror = function () {
    this.style.display = "none";
    const label = document.createElement("div");
    label.className = "card-fallback";
    label.textContent = card.name;
    el.appendChild(label);
  };
  el.appendChild(img);

  if (opts.selectable && opts.onClick) {
    el.classList.add("selectable");
    el.onclick = opts.onClick;
  }
  return el;
}

// ───────────────────────────────────────────────────────────────────────────
//  PROMPT PANEL — the reactive / contextual area.
//  Handles: challenge window, modifier window, and choice prompts (yes/no,
//  number, pool pick). Selection-from-the-board prompts (pick a hero/player/
//  hand card) are explained here but answered by clicking the board itself.
// ───────────────────────────────────────────────────────────────────────────
function renderPrompt() {
  const panel = $("prompt-panel");
  panel.innerHTML = "";
  panel.classList.remove("urgent");

  // 1) A card is on the table — opponents may challenge it.
  if (STATE.phase === "CHALLENGE_WINDOW") return renderChallengeWindow(panel);

  // 2) A roll is live (only happens during a challenge here) — play modifiers.
  if (STATE.phase === "ROLL_PENDING") return renderModifierWindow(panel);

  // 3) A card effect is paused waiting on a choice.
  if (STATE.phase === "AWAITING_CHOICE") return renderChoice(panel);

  // 4) Plain action phase.
  panel.textContent = isMyTurn()
    ? "Your turn — play a card, attack a monster, use a party hero, or draw."
    : `Waiting for ${currentName()} to act…`;
}

function renderChallengeWindow(panel) {
  panel.classList.add("urgent");
  const playerName = nameOf(STATE.pending_player_id);
  const cardName = STATE.pending_card ? STATE.pending_card.name : "a card";
  const iPlayed = STATE.pending_player_id === MY_ID;

  const title = document.createElement("div");
  title.className = "prompt-title";
  title.textContent = iPlayed
    ? `Your "${cardName}" is on the table — waiting to see if anyone challenges…`
    : `${playerName} is playing "${cardName}". Challenge it?`;
  panel.appendChild(title);

  if (!iPlayed) {
    const hasChallenges = (me().hand || []).some(c => c.card_type === "challenge");
    panel.appendChild(note(hasChallenges
      ? "Click a Challenge card in your hand to play it."
      : "You have no Challenge cards. (Resolves automatically.)"));
  }
  panel.appendChild(note("The window closes on its own after a few seconds."));
}

function renderModifierWindow(panel) {
  panel.classList.add("urgent");
  const title = document.createElement("div");
  title.className = "prompt-title";
  title.textContent = "A roll is in progress — play a Modifier to change it?";
  panel.appendChild(title);

  // Show the live rolls so players can decide.
  const rolls = STATE.players
    .filter(p => p.current_roll)
    .map(p => `${p.name}: ${p.current_roll}`).join("   ");
  if (rolls) panel.appendChild(note("Rolls — " + rolls));

  const mods = (me().hand || []).filter(c => c.card_type === "modifier");
  if (mods.length === 0) {
    panel.appendChild(note("You have no Modifier cards."));
  } else {
    mods.forEach(c => {
      const wrap = document.createElement("div");
      wrap.className = "modifier-opts";
      const label = document.createElement("span");
      label.textContent = `"${c.name}":`;
      label.style.marginRight = "6px";
      wrap.appendChild(label);
      // options is e.g. [1, -3] — one button per side.
      (c.options || [0]).forEach((opt, idx) => {
        const b = document.createElement("button");
        b.textContent = (opt >= 0 ? "+" : "") + opt;
        b.onclick = () => send("play_modifier", { uid: c.uid, choice: idx });
        wrap.appendChild(b);
      });
      panel.appendChild(wrap);
    });
  }
  panel.appendChild(note("Closes on its own after a few seconds."));
}

function renderChoice(panel) {
  const choice = myChoice();
  if (!choice) {
    panel.textContent = `Waiting for ${nameOf(STATE.choice_player_id)} to choose…`;
    return;
  }
  const title = document.createElement("div");
  title.className = "prompt-title";
  title.textContent = promptText(choice);
  panel.appendChild(title);

  if (choice === "CHOOSE_YES_NO") {
    ["Yes", "No"].forEach((label, idx) => {
      const b = document.createElement("button");
      b.textContent = label;
      b.onclick = () => send("submit_choice", { choice: idx });  // 0 = yes, 1 = no
      panel.appendChild(b);
    });
  } else if (choice === "CHOOSE_NUMBER") {
    const input = document.createElement("input");
    input.type = "number"; input.value = "0"; input.style.width = "70px";
    const b = document.createElement("button");
    b.textContent = "OK";
    b.onclick = () => send("submit_choice", { choice: parseInt(input.value || "0", 10) });
    panel.append(input, b);
  } else if (choice === "CHOOSE_CARD_FROM_POOL") {
    const row = document.createElement("div");
    row.className = "card-row";
    STATE.collected_cards.forEach(c => {
      row.appendChild(cardEl(c, { selectable: true,
        onClick: () => send("submit_choice", { target_card_uid: c.uid }) }));
    });
    panel.appendChild(row);
  } else {
    // The rest are answered by clicking a hero / player / hand card on the
    // board (see selectability rules in renderOpponents / renderMe).
    panel.appendChild(note("Click the highlighted target on the board."));
  }
}

// ───────────────────────────────────────────────────────────────────────────
//  OPPONENTS — name, leader, party, face-down hand, roll
// ───────────────────────────────────────────────────────────────────────────
function renderOpponents() {
  const box = $("opponents");
  box.innerHTML = "";
  opponents().forEach(p => {
    const el = document.createElement("div");
    el.className = "opponent";
    if (p.player_id === STATE.current_player_id) el.classList.add("turn-active");

    // Make the whole opponent panel clickable when the active prompt is
    // "choose a target player" — clicking anywhere on their area picks them.
    if (myChoice() === "CHOOSE_TARGET_PLAYER") {
      el.classList.add("selectable");
      el.onclick = () => send("submit_choice", { target_player_id: p.player_id });
    }

    const head = document.createElement("div");
    head.className = "opp-head";
    head.innerHTML = `<span class="opp-name">${escapeHtml(p.name)}</span>` +
      `<span class="roll">AP ${p.action_points} · roll ${p.current_roll}</span>`;
    el.appendChild(head);

    el.appendChild(subhead("Leader"));
    const leaderRow = document.createElement("div");
    leaderRow.className = "card-row";
    if (p.party_leader) leaderRow.appendChild(cardEl(p.party_leader, { mini: false }));
    el.appendChild(leaderRow);

    el.appendChild(subhead("Party"));
    const partyRow = document.createElement("div");
    partyRow.className = "card-row";
    p.party.forEach(c => partyRow.appendChild(heroSelectable(c, p)));
    el.appendChild(partyRow);

    el.appendChild(subhead(`Hand (${p.hand_count})`));
    const handRow = document.createElement("div");
    handRow.className = "card-row";
    for (let i = 0; i < p.hand_count; i++)
      handRow.appendChild(cardEl(null, { faceDown: true, mini: true }));
    el.appendChild(handRow);

    box.appendChild(el);
  });
}

// A party card on an OPPONENT becomes selectable when a choice targets an
// opponent's / any party's hero.
function heroSelectable(card, owner) {
  const choice = myChoice();
  const isHero = card.card_type === "hero";
  if (isHero && choice === "CHOOSE_HERO_FROM_OPPONENT_PARTY") {
    return cardEl(card, { selectable: true,
      onClick: () => send("submit_choice", { target_player_id: owner.player_id, target_hero_uid: card.uid }) });
  }
  if (isHero && choice === "CHOOSE_HERO_FROM_ANY_PARTY") {
    return cardEl(card, { selectable: true,
      onClick: () => send("submit_choice", { target_hero_uid: card.uid }) });
  }
  return cardEl(card);
}

// ───────────────────────────────────────────────────────────────────────────
//  MONSTER ROW — clickable to attack on your turn
// ───────────────────────────────────────────────────────────────────────────
function renderMonsterRow() {
  const row = $("monster-row");
  row.innerHTML = "";
  const canAttack = isMyTurn() && STATE.phase === "ACTION";
  STATE.monster_row.forEach(m => {
    row.appendChild(cardEl(m, {
      selectable: canAttack,
      onClick: canAttack ? () => send("attack_monster", { uid: m.uid }) : null,
    }));
  });
}

// ───────────────────────────────────────────────────────────────────────────
//  ME — leader, party (use ability), hand (play), action bar
// ───────────────────────────────────────────────────────────────────────────
function renderMe() {
  const p = me();
  $("me-name").textContent = p.name;
  $("me-ap").textContent = p.action_points;

  const leader = $("me-leader");
  leader.innerHTML = "";
  if (p.party_leader) leader.appendChild(cardEl(p.party_leader));

  const party = $("me-party");
  party.innerHTML = "";
  p.party.forEach(c => party.appendChild(myPartyCard(c)));

  const hand = $("me-hand");
  hand.innerHTML = "";
  (p.hand || []).forEach(c => hand.appendChild(myHandCard(c)));

  // Enable the turn buttons only when it's actually your action phase.
  const canAct = isMyTurn() && STATE.phase === "ACTION";
  document.querySelectorAll("#action-bar button").forEach(b => b.disabled = !canAct);
}

// A card in MY party: clickable to use its ability (ACTION), or to answer a
// "choose a hero from your own / any party" prompt.
function myPartyCard(card) {
  const choice = myChoice();
  const isHero = card.card_type === "hero";
  if (isHero && (choice === "CHOOSE_HERO_FROM_OWN_PARTY" || choice === "CHOOSE_HERO_FROM_ANY_PARTY")) {
    return cardEl(card, { selectable: true,
      onClick: () => send("submit_choice", { target_hero_uid: card.uid }) });
  }
  if (isHero && isMyTurn() && STATE.phase === "ACTION") {
    if (card.was_used_this_turn) {
      // Ability spent this turn — render as normal but visually dimmed.
      const el = cardEl(card);
      el.style.opacity = "0.45";
      el.title = "Already used this turn";
      return el;
    }
    return cardEl(card, { selectable: true,
      onClick: () => send("use_party_ability", { uid: card.uid }) });
  }
  return cardEl(card);
}

// A card in MY hand: clickable to play it (ACTION), or to answer a
// "choose a card from your hand" prompt.
function myHandCard(card) {
  const choice = myChoice();
  if (choice === "CHOOSE_CARD_FROM_OWN_HAND") {
    return cardEl(card, { selectable: true,
      onClick: () => send("submit_choice", { target_card_uid: card.uid }) });
  }

  // Modifiers are only playable during a roll window — not as a regular action.
  if (card.card_type === "modifier") {
    if (STATE.phase !== "ROLL_PENDING") return cardEl(card);
    // Two-sided modifier (+1 / -3): render inline choice buttons instead of
    // making the card itself clickable (player must pick which side to apply).
    if (card.options && card.options.length > 1) {
      const wrap = document.createElement("div");
      const base = cardEl(card);
      const opts = document.createElement("div");
      opts.className = "modifier-opts";
      card.options.forEach((opt, idx) => {
        const b = document.createElement("button");
        b.textContent = (opt >= 0 ? "+" : "") + opt;
        b.onclick = () => send("play_modifier", { uid: card.uid, choice: idx });
        opts.appendChild(b);
      });
      base.appendChild(opts);
      wrap.appendChild(base);
      return wrap;
    }
    // Single-value modifier: clicking the card plays it.
    return cardEl(card, { selectable: true,
      onClick: () => send("play_modifier", { uid: card.uid, choice: 0 }) });
  }

  // Challenge cards are only playable during the challenge window, and only by
  // opponents (the server enforces this — we just hide the button for the player
  // who played the card so the UI stays clean).
  if (card.card_type === "challenge") {
    const canChallenge = STATE.phase === "CHALLENGE_WINDOW"
      && STATE.pending_player_id !== MY_ID;
    if (!canChallenge) return cardEl(card);
    return cardEl(card, { selectable: true,
      onClick: () => send("play_challenge", { uid: card.uid }) });
  }

  // Heroes, magic, and items are played as normal actions on your turn.
  if (isMyTurn() && STATE.phase === "ACTION") {
    return cardEl(card, { selectable: true,
      onClick: () => send("play_card", { uid: card.uid }) });
  }
  return cardEl(card);
}

// ───────────────────────────────────────────────────────────────────────────
//  Small utilities
// ───────────────────────────────────────────────────────────────────────────
function note(text) {
  const d = document.createElement("div");
  d.className = "hint";
  d.textContent = text;
  return d;
}
function subhead(text) {
  const h = document.createElement("h3");
  h.textContent = text;
  return h;
}
function nameOf(id) {
  const p = STATE.players.find(x => x.player_id === id);
  return p ? p.name : "—";
}
const currentName = () => nameOf(STATE.current_player_id);

function promptText(choice) {
  return {
    CHOOSE_TARGET_PLAYER:            "Choose a player.",
    CHOOSE_HERO_FROM_OWN_PARTY:      "Choose a hero from YOUR party.",
    CHOOSE_HERO_FROM_ANY_PARTY:      "Choose a hero from ANY party.",
    CHOOSE_HERO_FROM_OPPONENT_PARTY: "Choose a hero from an OPPONENT's party.",
    CHOOSE_CARD_FROM_OWN_HAND:       "Choose a card from your hand.",
    CHOOSE_CARD_FROM_POOL:           "Choose a card from the pool.",
    CHOOSE_YES_NO:                   "Yes or no?",
    CHOOSE_NUMBER:                   "Pick a number.",
  }[choice] || "Make a choice.";
}

let toastTimer = null;
function flash(message) {
  const t = $("error-toast");
  t.textContent = message || "Something went wrong";
  t.classList.remove("hidden");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.add("hidden"), 3000);
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// ── Custom card tooltip ────────────────────────────────────────────────────
// Replaces native `title` so we can control font size and style.
const _tip = document.createElement("div");
_tip.id = "card-tooltip";
document.body.appendChild(_tip);

document.addEventListener("mouseover", e => {
  const card = e.target.closest("[data-tooltip]");
  if (!card) return;
  const [name, ...rest] = card.dataset.tooltip.split("\n");
  _tip.innerHTML = `<strong>${escapeHtml(name)}</strong>${rest.length ? "<br>" + escapeHtml(rest.join("\n")) : ""}`;
  _tip.classList.add("visible");
});
document.addEventListener("mousemove", e => {
  _tip.style.left = (e.clientX + 14) + "px";
  _tip.style.top  = (e.clientY + 14) + "px";
});
document.addEventListener("mouseout", e => {
  if (!e.target.closest("[data-tooltip]")) return;
  _tip.classList.remove("visible");
});
