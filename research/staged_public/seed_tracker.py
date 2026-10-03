"""Small public staged-coding fixture."""


class Tracker:
    def __init__(self):
        self._items = []
        self._next_id = 1
