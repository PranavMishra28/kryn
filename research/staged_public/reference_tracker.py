"""Trusted reference for no-model oracle control."""


class Tracker:
    def __init__(self):
        self._items = []
        self._next_id = 1

    def add(self, title):
        title = title.strip()
        if not title:
            raise ValueError("empty title")
        item_id = self._next_id
        self._next_id += 1
        self._items.append({"id": item_id, "title": title, "done": False})
        return item_id

    def list_items(self):
        return [item.copy() for item in self._items]

    def complete(self, item_id):
        for item in self._items:
            if item["id"] == item_id:
                if item["done"]:
                    return False
                item["done"] = True
                return True
        raise KeyError(item_id)

    def snapshot(self):
        return tuple((item["id"], item["title"], item["done"])
                     for item in self._items)
