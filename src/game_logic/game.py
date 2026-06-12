from typing import *
from abc import ABC
from player import Player

class Game():
    def __init__(self) -> None:
        self.players:List[Player] = []
        pass
    def add_player(self, player: Player) -> None:
        self.players.append(player)