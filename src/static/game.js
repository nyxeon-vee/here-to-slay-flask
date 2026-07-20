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
socket.on("discard_pile", (data) => renderDiscardModal(data.cards));

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

// Discard pill → request full pile; close button hides the modal.
$("discard-pill").onclick = () => send("show_discard");
$("discard-close-btn").onclick = () => $("discard-modal").classList.add("hidden");
$("discard-modal").addEventListener("click", e => {
  if (e.target === $("discard-modal")) $("discard-modal").classList.add("hidden");
});

function renderDiscardModal(cards) {
  const grid = $("discard-card-grid");
  grid.innerHTML = "";
  if (cards.length === 0) {
    grid.textContent = "Discard pile is empty.";
  } else {
    cards.forEach(c => grid.appendChild(cardEl(c)));
  }
  $("discard-modal").classList.remove("hidden");
}

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
  renderActionOverlay();
  renderPrompt();
  renderOpponents();
  renderMonsterRow();
  renderMe();
  renderLog();
}

// ── Event log panel — auto-scrolls to the newest entry ─────────────────────
function renderLog() {
  const box = $("game-log-entries");
  const stuckToBottom =                       // don't yank the scroll if the
    box.scrollHeight - box.scrollTop - box.clientHeight < 20; // user scrolled up
  box.innerHTML = "";
  (STATE.log || []).forEach(e => {
    const d = document.createElement("div");
    d.className = "log-entry " + (e.kind || "info");
    d.textContent = e.text;
    box.appendChild(d);
  });
  if (stuckToBottom) box.scrollTop = box.scrollHeight;
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

// ── Countdown timer ────────────────────────────────────────────────────────
const TIMER_SECS = { CHALLENGE_WINDOW: 8, ROLL_PENDING: 6 };
let _timerInterval = null;

function _setTimerArc(pct) {
  $("timer-arc").setAttribute("stroke-dasharray", `${pct.toFixed(1)} 100`);
}

function startTimer(total) {
  clearInterval(_timerInterval);
  let remaining = total;
  function tick() {
    $("timer-secs").textContent = remaining;
    _setTimerArc((remaining / total) * 100);
    if (remaining === 0) { clearInterval(_timerInterval); return; }
    remaining--;
  }
  tick();
  _timerInterval = setInterval(tick, 1000);
}

function updateTimer() {
  const total = TIMER_SECS[STATE.phase];
  if (!total) {
    clearInterval(_timerInterval);
    $("ao-timer").classList.add("hidden");
    return;
  }
  $("ao-timer").classList.remove("hidden");
  // Every state update in a timed phase means the server restarted its timer
  // (modifier played, challenge played, or just entered this phase) — mirror it.
  startTimer(total);
}

// ── Challenge dice helper — always 2-column layout ─────────────────────────
function renderChallengeDice(ctx) {
  const cr = ctx.challenger_roll;   // null before anyone challenges
  const cd = ctx.challenged_roll;   // null roll until step 2

  const diceRow = $("roll-dice");
  diceRow.innerHTML = "";
  $("roll-who").textContent = "";
  $("roll-total").textContent = "";

  const vsEl = document.createElement("div");
  vsEl.className = "challenge-rolls";

  const left  = cr || { player_id: null, name: "Challenger", roll: null };
  const right = cd || { player_id: null, name: "Challenged", roll: null };

  [[left, "Challenger"], [right, "Challenged"]].forEach(([info, label]) => {
    const col = document.createElement("div");
    col.className = "challenge-roll-col";

    const nameEl = document.createElement("div");
    nameEl.className = "challenge-roll-name";
    nameEl.textContent = info.player_id === MY_ID
      ? `${label} (You)`
      : (info.name && info.name !== label ? `${label}: ${escapeHtml(info.name)}` : label);

    const rollEl = document.createElement("div");
    rollEl.className = "challenge-roll-total";
    rollEl.textContent = info.roll != null ? info.roll : "?";

    col.append(nameEl, rollEl);
    vsEl.appendChild(col);
  });

  diceRow.appendChild(vsEl);
}

function renderActionOverlay() {
  const overlay     = $("action-overlay");
  const ctx         = STATE.action_context;
  const diceSection = $("ao-dice-section");
  const interactive = $("ao-interactive");
  interactive.innerHTML = "";

  const phase = STATE.phase;
  const isChallengPhase = ctx && (ctx.phase === "challenge_window" || ctx.phase === "challenge_roll");

  // Hide the overlay and timer when there's nothing contextual to show.
  if (!ctx && phase !== "AWAITING_CHOICE") {
    overlay.classList.add("hidden");
    updateTimer();
    return;
  }
  overlay.classList.remove("hidden");
  updateTimer();

  // ── Label ────────────────────────────────────────────────────────────────
  const labelEl = $("ao-label");
  if (ctx) {
    const isSelf = ctx.player_id === MY_ID;
    const who    = isSelf ? "You" : escapeHtml(ctx.player_name);
    const verb   = ctx.label || ctx.phase.replace(/_/g, " ");
    labelEl.textContent = isSelf ? `You — ${verb}` : `${who} — ${verb}`;
  } else {
    labelEl.textContent = "Choose…";
  }

  // ── Card thumbnail + name + description ──────────────────────────────────
  const cardArea = $("ao-card-area");
  cardArea.innerHTML = "";
  const card = ctx && ctx.card;
  if (card) {
    const wrap = document.createElement("div");
    wrap.className = "ao-card";
    const folder = CARD_TYPE_FOLDER[card.card_type] || card.card_type;
    const img = document.createElement("img");
    img.src = `/static/img/card/${folder}/${card.card_id}.png`;
    img.alt = card.name;
    img.className = "ao-card-img";
    img.onerror = () => { img.style.display = "none"; };
    const info = document.createElement("div");
    info.className = "ao-card-info";
    info.innerHTML =
      `<div class="ao-card-name">${escapeHtml(card.name)}</div>` +
      `<div class="ao-card-desc">${escapeHtml(card.description)}</div>`;
    wrap.append(img, info);
    cardArea.appendChild(wrap);
  }

  // ── Dice section ─────────────────────────────────────────────────────────
  const lr = STATE.last_roll;
  if (isChallengPhase) {
    // Challenge: always show two columns (? until rolled)
    diceSection.classList.remove("hidden");
    renderChallengeDice(ctx);
  } else if (phase === "ROLL_PENDING" && lr) {
    // Hero ability or monster attack — single roll with dice faces
    diceSection.classList.remove("hidden");
    const d1 = Math.floor(lr.initial / 2);
    const d2 = lr.initial - d1;
    const current = lr.current;
    const delta = current - lr.initial;
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
    $("roll-total").textContent = `= ${current}${deltaStr}`;
  } else {
    diceSection.classList.add("hidden");
  }

  // ── Interactive section ───────────────────────────────────────────────────
  if (phase === "CHALLENGE_WINDOW") {
    _buildChallengeWindowUI(interactive);
  } else if (phase === "ROLL_PENDING") {
    _buildModifierUI(interactive);
  } else if (phase === "AWAITING_CHOICE") {
    _buildChoiceUI(interactive);
  }
}

function _buildChallengeWindowUI(box) {
  const iPlayed = STATE.pending_player_id === MY_ID;
  const cardName = STATE.pending_card ? STATE.pending_card.name : "a card";
  const title = document.createElement("div");
  title.className = "prompt-title";
  title.textContent = iPlayed
    ? `Your "${cardName}" is on the table — waiting for challenges…`
    : `Will anyone challenge "${cardName}"?`;
  box.appendChild(title);

  if (!iPlayed) {
    const hasChallenges = (me().hand || []).some(c => c.card_type === "challenge");
    box.appendChild(note(hasChallenges
      ? "Click a Challenge card in your hand to play it."
      : "You have no Challenge cards."));
  }
}

function _buildModifierUI(box) {
  const mods = (me().hand || []).filter(c => c.card_type === "modifier");
  if (mods.length === 0) {
    box.appendChild(note("You have no Modifier cards."));
    return;
  }
  mods.forEach(c => {
    const wrap = document.createElement("div");
    wrap.className = "modifier-opts";
    const label = document.createElement("span");
    label.textContent = `"${c.name}":`;
    label.style.marginRight = "6px";
    wrap.appendChild(label);
    (c.options || [0]).forEach((opt, idx) => {
      const b = document.createElement("button");
      b.textContent = (opt >= 0 ? "+" : "") + opt;
      b.onclick = () => send("play_modifier", { uid: c.uid, choice: idx });
      wrap.appendChild(b);
    });
    box.appendChild(wrap);
  });
}

function _buildChoiceUI(box) {
  const choice = myChoice();
  if (!choice) {
    box.appendChild(note(`Waiting for ${nameOf(STATE.choice_player_id)} to choose…`));
    return;
  }
  const title = document.createElement("div");
  title.className = "prompt-title";
  title.textContent = STATE.choice_message || promptText(choice);
  box.appendChild(title);

  if (choice === "CHOOSE_YES_NO") {
    const row = document.createElement("div");
    row.style.display = "flex"; row.style.gap = "8px";
    ["Yes", "No"].forEach((label, idx) => {
      const b = document.createElement("button");
      b.textContent = label;
      b.onclick = () => send("submit_choice", { choice: idx });
      row.appendChild(b);
    });
    box.appendChild(row);
  } else if (choice === "CHOOSE_NUMBER") {
    const row = document.createElement("div");
    row.style.display = "flex"; row.style.gap = "8px"; row.style.alignItems = "center";
    const input = document.createElement("input");
    input.type = "number"; input.value = "0"; input.style.width = "70px";
    const b = document.createElement("button");
    b.textContent = "OK";
    b.onclick = () => send("submit_choice", { choice: parseInt(input.value || "0", 10) });
    row.append(input, b);
    box.appendChild(row);
  } else if (choice === "CHOOSE_CARD_FROM_POOL") {
    const row = document.createElement("div");
    row.className = "card-row";
    STATE.collected_cards.forEach(c => {
      row.appendChild(cardEl(c, { selectable: true,
        onClick: () => send("submit_choice", { target_card_uid: c.uid }) }));
    });
    box.appendChild(row);
  } else {
    box.appendChild(note("Click the highlighted target on the board."));
  }
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
  if (card.activation_roll) {
    el.dataset.roll = JSON.stringify(card.activation_roll);
  }
  if (card.hero_class) {
    el.dataset.heroClass = card.hero_class;   // plain string, e.g. "bard"
  }

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
  // Only shown during plain ACTION phase — everything else is in the action overlay.
  const show = STATE.phase === "ACTION";
  panel.style.display = show ? "" : "none";
  if (!show) return;
  panel.textContent = isMyTurn()
    ? "Your turn — play a card, attack a monster, use a party hero, or draw."
    : `Waiting for ${currentName()} to act…`;
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
    const badges =
      (p.steal_protected   ? `<span class="protected-badge" title="Party cannot be stolen from">🛡 No steal</span> ` : "") +
      (p.destroy_protected ? `<span class="protected-badge" title="Heroes cannot be destroyed">🛡 No destroy</span> ` : "");
    head.innerHTML = `<span class="opp-name">${escapeHtml(p.name)}</span>` +
      `<span class="roll">${badges}AP ${p.action_points} · roll ${p.current_roll}</span>`;
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

// Wrap a hero element with its equipped item displayed below it.
function stackWithItem(card, heroEl) {
  if (!card.item) return heroEl;
  const stack = document.createElement("div");
  stack.className = "party-hero-stack";
  stack.appendChild(heroEl);
  const itemEl = cardEl(card.item);
  itemEl.classList.add("party-item-card");
  stack.appendChild(itemEl);
  return stack;
}



// A hero in MY party whose equipped item is CURSED — the item card (peeking
// below the hero) becomes the clickable target. Heroes with no item, or with
// a non-cursed item, render normally. Answers CHOOSE_CURSED_ITEM_FROM_OWN_PARTY,
// whose yield returns (hero, item) — so we send both uids.
function cursedItemSelectable(card) {
  const heroEl = cardEl(card);
  if (!card.item || !card.item.is_cursed) {
    return stackWithItem(card, heroEl);   // not a valid target — plain render
  }
  const stack = document.createElement("div");
  stack.className = "party-hero-stack";
  stack.appendChild(heroEl);
  const itemEl = cardEl(card.item, { selectable: true,
    onClick: () => send("submit_choice", { target_hero_uid: card.uid, target_card_uid: card.item.uid }) });
  itemEl.classList.add("party-item-card");
  stack.appendChild(itemEl);
  return stack;
}


// A party card on an OPPONENT becomes selectable when a choice targets an
// opponent's / any party's hero.
function heroSelectable(card, owner) {
  const choice = myChoice();
  const isHero = card.card_type === "hero";
  if (isHero && choice === "CHOOSE_HERO_FROM_OPPONENT_PARTY") {
    return stackWithItem(card, cardEl(card, { selectable: true,
      onClick: () => send("submit_choice", { target_player_id: owner.player_id, target_hero_uid: card.uid }) }));
  }
  // Stealing respects Calming Voice, destroying respects Mighty Blade —
  // protected parties render greyed-out instead of selectable.
  const protectedChoices = {
    CHOOSE_HERO_TO_STEAL:   "steal_protected",
    CHOOSE_HERO_TO_DESTROY: "destroy_protected",
  };
  if (isHero && protectedChoices[choice]) {
    if (owner[protectedChoices[choice]]) {
      const el = cardEl(card);
      el.style.opacity = "0.45";
      return stackWithItem(card, el);
    }
    return stackWithItem(card, cardEl(card, { selectable: true,
      onClick: () => send("submit_choice", { target_player_id: owner.player_id, target_hero_uid: card.uid }) }));
  }
  if (isHero && choice === "CHOOSE_HERO_FROM_ANY_PARTY") {
    return stackWithItem(card, cardEl(card, { selectable: true,
      onClick: () => send("submit_choice", { target_hero_uid: card.uid }) }));
  }
  return stackWithItem(card, cardEl(card));
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
  if (isHero && choice === "CHOOSE_CURSED_ITEM_FROM_OWN_PARTY") {
    return cursedItemSelectable(card);
  }
  if (isHero && (choice === "CHOOSE_HERO_FROM_OWN_PARTY" || choice === "CHOOSE_HERO_FROM_ANY_PARTY")) {
    return stackWithItem(card, cardEl(card, { selectable: true,
      onClick: () => send("submit_choice", { target_hero_uid: card.uid }) }));
  }
  if (isHero && isMyTurn() && STATE.phase === "ACTION") {
    if (card.was_used_this_turn || card.is_sealed) {
      const el = cardEl(card);
      el.style.opacity = "0.45";
      el.title = card.is_sealed ? `Sealed by ${card.item.name} — ability unusable`
                                : "Already used this turn";
      return stackWithItem(card, el);
    }
    return stackWithItem(card, cardEl(card, { selectable: true,
      onClick: () => send("use_party_ability", { uid: card.uid }) }));
  }
  return stackWithItem(card, cardEl(card));
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
    CHOOSE_HERO_TO_STEAL:            "Choose a hero to STEAL (protected parties are greyed out).",
    CHOOSE_HERO_TO_DESTROY:          "Choose a hero to DESTROY (protected parties are greyed out).",
    CHOOSE_CARD_FROM_OWN_HAND:       "Choose a card from your hand.",
    CHOOSE_CURSED_ITEM_FROM_OWN_PARTY: "Choose a CURSED item in your party.",
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
const CLASS_COLORS = {
  fighter:  "#eb5757",
  ranger:   "#6fcf97",
  wizard:   "#bb6bd9",
  bard:     "#f2c14e",
  thief:    "#b0b0b0",
  guardian: "#7ec8f2",
};
const _tip = document.createElement("div");
_tip.id = "card-tooltip";
document.body.appendChild(_tip);

document.addEventListener("mouseover", e => {
  const card = e.target.closest("[data-tooltip]");
  if (!card) return;
  const [name, ...rest] = card.dataset.tooltip.split("\n");
  let html = `<strong>${escapeHtml(name)}</strong>`;
  if (rest.length) html += `<br><span class="tip-desc">${escapeHtml(rest.join("\n"))}</span>`;

  if (card.dataset.roll) {
    const roll = JSON.parse(card.dataset.roll);
    const atLeast = roll.condition === "at_least";
    const sign    = atLeast ? "+" : "−";
    const color   = atLeast ? "#6fcf97" : "#eb5757";
    html += `<br><span class="tip-roll" style="color:${color}">`
          + `Roll ${sign}${roll.value} or ${atLeast ? "higher" : "lower"}`
          + `</span>`;
  }
  if (card.dataset.heroClass) {
    const cls = card.dataset.heroClass;       // plain string set by cardEl
    const clsColor = CLASS_COLORS[cls] || "#c7e0cf";
    html += `<br><span class="tip-class" style="color:${clsColor}">`
          + `CLASS: ${escapeHtml(cls.toUpperCase())}`
          + `</span>`;
  }

  _tip.innerHTML = html;
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
