import os
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from app import config
from app.db import repository as repo
from app.db.database import init_db
from app.services import pokeapi

INDEX = [
    {"id": 1, "name": "bulbasaur", "types": ["grass", "poison"]},
    {"id": 4, "name": "charmander", "types": ["fire"]},
    {"id": 5, "name": "charmeleon", "types": ["fire"]},
    {"id": 122, "name": "mr-mime", "types": ["psychic", "fairy"]},
]


def detail(pokemon_id: int, name: str, types: list[str], hp: int = 40) -> dict:
    stats = {"hp": hp, "attack": 50, "defense": 50, "special_attack": 50, "special_defense": 50, "speed": 50}
    return {"id": pokemon_id, "name": name, "types": types, "height": 0.6, "weight": 8.5,
            "abilities": ["blaze"], "stats": stats, "sprite": "x"}


def custom_data(**overrides) -> dict:
    data = {"name": None, "type1": "fire", "type2": None, "hp": 50, "attack": 50, "defense": 50,
            "special_attack": 50, "special_defense": 50, "speed": 50, "height": 0.5, "weight": 8.0}
    return {**data, **overrides}


class DBTestCase(unittest.IsolatedAsyncioTestCase):
    """Cada test usa una BD SQLite nueva en un archivo temporal y nunca sale a internet."""

    def setUp(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))
        path = os.path.join(tmp, "test.db")
        db_patch = patch.object(config, "DB_PATH", path)
        db_patch.start()
        self.addCleanup(db_patch.stop)

        self.fetch_index = AsyncMock(return_value=INDEX)
        self.fetch_detail = AsyncMock(side_effect=lambda name: detail(4, "charmander", ["fire"]))
        for name, mock in (("fetch_index", self.fetch_index), ("fetch_pokemon_detail", self.fetch_detail)):
            p = patch.object(pokeapi, name, mock)
            p.start()
            self.addCleanup(p.stop)

        init_db()
        repo.save_index(INDEX)