import unittest
from unittest.mock import AsyncMock, patch

import httpx

from app.services import pokeapi

RAW = {"pokemon": [{
    "id": 4, "name": "charmander", "height": 6, "weight": 85,
    "pokemontypes": [{"type": {"name": "fire"}}],
    "pokemonabilities": [{"ability": {"name": "blaze"}}],
    "pokemonstats": [{"base_stat": 39, "stat": {"name": "hp"}}, {"base_stat": 60, "stat": {"name": "special-attack"}}],
}]}


def fake_client(handler):
    real = httpx.AsyncClient
    return lambda **kw: real(transport=httpx.MockTransport(handler), **kw)


class TestPokeAPIClient(unittest.IsolatedAsyncioTestCase):
    async def test_converts_units_and_stat_names(self):
        with patch.object(pokeapi, "_post", AsyncMock(return_value=RAW)):
            d = await pokeapi.fetch_pokemon_detail(" Charmander ")
        self.assertEqual((d["height"], d["weight"]), (0.6, 8.5))
        self.assertEqual(d["stats"], {"hp": 39, "special_attack": 60})
        self.assertTrue(d["sprite"].endswith("/4.png"))

    async def test_unknown_pokemon_returns_none(self):
        with patch.object(pokeapi, "_post", AsyncMock(return_value={"pokemon": []})):
            self.assertIsNone(await pokeapi.fetch_pokemon_detail("fakemon"))

    async def test_every_failure_becomes_pokeapierror(self):
        cases = {
            "rate limit": lambda r: httpx.Response(429),
            "graphql error": lambda r: httpx.Response(200, json={"errors": [{"message": "bad"}]}),
            "not json": lambda r: httpx.Response(200, text="<html>"),
            "timeout": lambda r: (_ for _ in ()).throw(httpx.ConnectTimeout("t")),
        }
        for label, handler in cases.items():
            with self.subTest(label), patch.object(pokeapi.httpx, "AsyncClient", fake_client(handler)):
                with self.assertRaises(pokeapi.PokeAPIError):
                    await pokeapi.fetch_pokemon_detail("charmander")