"""
Custom exceptions for game-rule violations.

These are raised by Game/Player methods when an action is illegal (wrong phase,
not your turn, card not where it should be, etc.). The Flask/SocketIO layer is
expected to catch these and turn them into friendly error messages for the
client — the game state is left unchanged when one is raised.
"""


class CardNotInPartyError(Exception):
    pass


class InvalidPhaseError(Exception):
    pass


class PlayerNotEnoughActionPointsError(Exception):
    pass


class CardNotInHandError(Exception):
    pass


class PartyNotFulfillRequiermentError(Exception):
    pass


class PlayerHandEmptyError(Exception):
    pass
