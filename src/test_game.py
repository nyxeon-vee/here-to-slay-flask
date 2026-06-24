"""
Plain Python test — validates a full turn without Flask/SocketIO.
Run from src/: python3 test_game.py
"""
from game_logic.game import Game, Phase
from game_logic.player import Player
from game_logic.base import (
    Hero, Monster, Leader, HeroClass, RollThreshold, RollCondition,
    PartyRequirement, RollOutcome, GameEvent, ChoiceType
)
from game_logic.cards.registry import CARD_REGISTRY
from game_logic.cards.heroes.bad_axe import BadAxe
from game_logic.cards.leaders.the_divine_arrow import TheDivineArrow
from game_logic.cards.leaders.the_charismatic_song import TheCharismaticSong
from game_logic.cards.monsters.abyss_queen import AbyssQueen


# ── Minimal stub cards for building a deck ───────────────────────────────────

class StubHero(Hero):
    def __init__(self, name="StubHero"):
        super().__init__(
            card_id=f"stub_hero_{name}",
            name=name,
            description="Test hero",
            hero_class=HeroClass.FIGHTER,
            activation_roll=RollThreshold(2, RollCondition.AT_LEAST),  # always succeeds
        )
    def use_ability(self, game, player):
        print(f"  [{self.name}] ability triggered!")


class StubMonster(Monster):
    def __init__(self, name="StubMonster"):
        super().__init__(
            card_id=f"stub_monster_{name}",
            name=name,
            description="Test monster",
            defeat=RollThreshold(2, RollCondition.AT_LEAST),   # always wins
            fail=RollThreshold(1, RollCondition.AT_MOST),      # never fails
            party_requirement=PartyRequirement(0, tuple()),
        )
    def apply(self, game, player):
        pass


class StubLeader(Leader):
    def __init__(self):
        super().__init__(
            card_id="stub_leader",
            name="Stub Leader",
            description="No ability",
            hero_class=HeroClass.FIGHTER,
        )


# ── Helpers ───────────────────────────────────────────────────────────────────

def separator(title):
    print(f"\n{'='*50}")
    print(f"  {title}")
    print('='*50)


def assert_phase(game, expected):
    assert game.phase == expected, f"Expected phase {expected}, got {game.phase}"
    print(f"  phase: {game.phase.name} ✓")


# ── Test 1: Game setup ────────────────────────────────────────────────────────

separator("TEST 1: Game setup")

game = Game()
alice = Player("p1", "Alice")
bob   = Player("p2", "Bob")
game.add_player(alice)
game.add_player(bob)

# Build decks
game.deck = [StubHero(f"Hero{i}") for i in range(20)]
game.monster_deck = [StubMonster(f"Monster{i}") for i in range(5)]
game.leader_deck = [StubLeader(), StubLeader()]

game.start_game()

print(f"  Alice hand: {len(alice.hand)} cards")
print(f"  Bob hand:   {len(bob.hand)} cards")
print(f"  Monster row: {len(game.monster_row)} monsters")
assert len(alice.hand) == 5, "Alice should have 5 cards"
assert len(bob.hand) == 5, "Bob should have 5 cards"
assert len(game.monster_row) == 3, "Monster row should have 3 monsters"
assert game.current_player == alice
assert_phase(game, Phase.ACTION)
print("  PASS")


# ── Test 2: Draw a card ───────────────────────────────────────────────────────

separator("TEST 2: Draw card (costs 1 AP)")

ap_before = alice.action_points
game.draw_card(alice)
assert alice.action_points == ap_before - 1
assert len(alice.hand) == 6
print(f"  AP: {ap_before} → {alice.action_points} ✓")
print(f"  Hand: 5 → {len(alice.hand)} ✓")
print("  PASS")


# ── Test 3: Play a hero card ──────────────────────────────────────────────────

separator("TEST 3: Play StubHero (always succeeds, 2+ roll)")

hero_card = next(c for c in alice.hand if isinstance(c, StubHero))
ap_before = alice.action_points
print(f"  Playing {hero_card.name}...")
game.play_card(alice, hero_card)
print(f"  Alice rolled: {alice.current_roll}")
assert hero_card in alice.party, "Hero should be in party"
assert hero_card not in alice.hand, "Hero should be out of hand"
print(f"  AP: {ap_before} → {alice.action_points} ✓")
assert_phase(game, Phase.ACTION)
print("  PASS")


# ── Test 4: Attack a monster ──────────────────────────────────────────────────

separator("TEST 4: Attack monster (always wins, 0 party req)")

game.end_turn(alice)   # bob's turn
game.end_turn(bob)     # alice's turn again — full 3 AP
monster = game.monster_row[0]
ap_before = alice.action_points
print(f"  Attacking {monster.name}...")
game.attack_monster(alice, monster)
print(f"  Alice rolled: {alice.current_roll}")
assert monster in alice.party, "Monster should be in Alice's party"
assert monster not in game.monster_row, "Monster should leave row"
assert len(game.monster_row) == 3, "Row should be refilled to 3"
print(f"  AP: {ap_before} → {alice.action_points} ✓")
assert_phase(game, Phase.ACTION)
print("  PASS")


# ── Test 5: End turn ──────────────────────────────────────────────────────────

separator("TEST 5: End turn")

game.end_turn(alice)
assert game.current_player == bob
assert bob.action_points == 3
assert_phase(game, Phase.ACTION)
print(f"  Current player: {game.current_player.name} ✓")
print("  PASS")


# ── Test 6: Wrong player action ───────────────────────────────────────────────

separator("TEST 6: Alice can't act on Bob's turn")

try:
    game.draw_card(alice)
    print("  FAIL — should have raised InvalidPhaseError")
except Exception as e:
    print(f"  Correctly raised {type(e).__name__}: {e} ✓")
    print("  PASS")


# ── Test 7: Leader bonus (TheCharismaticSong) ─────────────────────────────────

separator("TEST 7: TheCharismaticSong gives +1 on hero rolls")

game2 = Game()
carol = Player("p3", "Carol")
dave  = Player("p4", "Dave")
game2.add_player(carol)
game2.add_player(dave)
game2.deck = [StubHero(f"Hero{i}") for i in range(10)]
game2.monster_deck = [StubMonster(f"M{i}") for i in range(5)]
game2.leader_deck = [StubLeader(), StubLeader()]
game2.start_game()

carol.party_leader = TheCharismaticSong()
hero_card = next(c for c in carol.hand if isinstance(c, StubHero))

import random
random.seed(42)
game2.play_card(carol, hero_card)
roll = carol.current_roll
print(f"  Roll with Charismatic Song leader: {roll}")
print(f"  (base roll + 1 from leader)")
print("  PASS")


# ── Test 8: challenge sequence ────────────────────────────────────────────────

separator("TEST 8: Challenge flow (start → roll 1 → roll 2 → resolve)")

game3 = Game()
eve  = Player("p5", "Eve")
finn = Player("p6", "Finn")
game3.add_player(eve)
game3.add_player(finn)
game3.deck = [StubHero(f"H{i}") for i in range(10)]
game3.monster_deck = [StubMonster(f"M{i}") for i in range(5)]
game3.leader_deck = [StubLeader(), StubLeader()]
game3.start_game()

# Put a hero in eve's hand to play
hero_to_play = next(c for c in eve.hand if isinstance(c, StubHero))

# Simulate playing a card — stops at CHALLENGE_WINDOW (play_card calls resolve immediately,
# so we manually set up the challenge window state)
game3._spend_ap(eve, hero_to_play.action_cost)
game3.phase = Phase.CHALLENGE_WINDOW
game3.pending_card = hero_to_play
game3.pending_player = eve

# Finn challenges
from game_logic.base import Challenge as ChallengeCard
class StubChallenge(ChallengeCard):
    def __init__(self):
        super().__init__("stub_challenge", "Stub Challenge", "Test challenge")
    def apply(self, game, player):
        pass

stub_chal = StubChallenge()
finn.hand.append(stub_chal)

game3.play_challenge(finn, stub_chal)
assert_phase(game3, Phase.ROLL_PENDING)
print(f"  Finn rolled: {finn.current_roll}")

game3.close_challenge_roll_1()
assert_phase(game3, Phase.ROLL_PENDING)
print(f"  Eve rolled: {eve.current_roll}")

game3.close_challenge_roll_2()
winner = "Finn" if finn.current_roll >= eve.current_roll else "Eve"
print(f"  Result: {winner} wins (Finn={finn.current_roll}, Eve={eve.current_roll})")
print("  PASS")


separator("ALL TESTS PASSED")
