### About
The goal of this project is to recreate the board game "Here to Slay" using python module Flask as a backend. The game will be entirely made as a web app with lobbies and players choosing their name and creating their game and inviting their friends!

### HTML response Endpoints
1. /lobby/ 
    - This endpoint will be the main endpoint that the user first sees
2. /game/{game_id} 
    - This is where the game is played, When the game isnt started The user is asked if they want to join the game.
    - If the game is started the user gets a message that the game is started and goes back to /lobby

### /game/ HTTP Endpoints
1. /start_game POST — starts the game, transitions lobby to DRAW phase
2. /game_state GET — returns filtered state for the requesting player (opponents' hands shown as count only)

### SocketIO Events
Game actions and real-time updates are handled via Flask-SocketIO instead of polling.

**Client → Server**
| Event | Payload | Description |
|---|---|---|
| `join_game` | `{ game_id }` | Join the game room on connect |
| `play_card` | `{ game_id, card_id }` | Play a card from hand (validated against current phase) |
| `attack_monster` | `{ game_id, monster_id }` | Declare an attack, transitions to ROLL_PENDING |
| `roll_dice` | `{ game_id }` | Roll the dice, only valid in ROLL_PENDING |
| `end_turn` | `{ game_id }` | End your turn |
| `discard_hand` | `{ game_id }` | Voluntarily discard your hand |

**Server → Client (broadcast to room)**
| Event | Payload | Description |
|---|---|---|
| `game_event` | `{ type, player_id, ... }` | Any public state change (card played, monster attacked, etc.) |
| `phase_changed` | `{ phase, active_player }` | Phase transition — clients use this to gate UI buttons |
| `dice_result` | `{ result, modifiers }` | Dice roll outcome after all modifiers resolved |
| `player_joined` | `{ player_id, name }` | A player joined the game room |
| `turn_ended` | `{ next_player }` | Active player changed |

**Server → Client (private, single player)**
| Event | Payload | Description |
|---|---|---|
| `hand_updated` | `{ cards }` | Your hand after drawing, playing, or discarding |



### Structure
```
src/
├── app.py
├── blueprints/
│   ├── lobby.py
│   └── game.py
├── templates/
│   ├── lobby/
│   │   └── index.html
│   └── game/
│       └── index.html
├── game_logic/
│   ├── game.py
│   └── cards/
│       ├── monsters/
│       ├── heroes/
│       ├── leaders/
│       ├── modifiers/
│       ├── items/
│       ├── challenge/
│       └── magic/
└── static/
    ├── css/
    │   └── style.css
    ├── img/
    │   └── cards/
    │       ├── monsters/
    │       ├── heroes/
    │       ├── leaders/
    │       ├── modifiers/
    │       ├── items/
    │       ├── challenge/
    │       └── magic/
    └── js/
```

### Game Logic

**Class Hierarchy**
```
Card(ABC)
├── Hero(Card)       → MightyBlade(Hero), Bard(Hero), ...
├── Monster(Card)    → Lancer(Monster), ...
├── Item(Card)
├── Magic(Card)
├── Modifier(Card)
├── Challenge(Card)
└── Leader(Card)
```

Each card type adds shared behavior at its level. Specific cards only implement `apply(game, player)` which contains that card's effect. Logic lives where it belongs:
- **Card behavior** → `card.apply(game, player)`
- **Turn/phase management** → `Game` class
- **Roll resolution** → `game.resolve_roll(result)`

**Card Registry**

Cards are registered by ID so they can be instantiated without importing every class explicitly. Used when building decks or restoring game state.

```python
CARD_REGISTRY = {}

def register(card_id):
    def decorator(cls):
        CARD_REGISTRY[card_id] = cls
        return cls
    return decorator

@register("mighty_blade")
class MightyBlade(Hero):
    ...

card = CARD_REGISTRY["mighty_blade"]()
```

**Structure**
```
game_logic/
├── game.py        # Game class — state, phases, turn management
├── player.py      # Player class — hand, party, deck
└── cards/
    ├── base.py    # Card(ABC), Hero(Card), Monster(Card), etc.
    ├── registry.py
    ├── heroes/
    ├── monsters/
    ├── leaders/
    ├── modifiers/
    ├── items/
    ├── challenge/
    └── magic/
```