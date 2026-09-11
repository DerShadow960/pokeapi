import httpx
from app import config

DETAIL_QUERY = """
query PokemonDetail($name: String!) {
  pokemon(where: {name: {_eq: $name}}, limit: 1) {
    id
    name
    height
    weight
    pokemontypes(order_by: {slot: asc}) { type { name } }
    pokemonabilities { ability { name } }
    pokemonstats { base_stat stat { name } }
  }
}
"""


class PokeAPIError(Exception):
    """PokéAPI no respondió, respondió con error o con algo que no es JSON."""


async def _post(query: str, variables: dict) -> dict:
    try:
        async with httpx.AsyncClient(timeout=config.POKEAPI_TIMEOUT) as client:
            resp = await client.post(config.POKEAPI_URL, json={"query": query, "variables": variables})
            resp.raise_for_status()
            body = resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise PokeAPIError(str(exc)) from exc
    if body.get("errors"):
        raise PokeAPIError(body["errors"][0].get("message", "GraphQL error"))
    return body["data"]


def _to_detail(raw: dict) -> dict:
    return {
        "id": raw["id"],
        "name": raw["name"],
        "height": raw["height"] / 10,  # decímetros -> metros
        "weight": raw["weight"] / 10,  # hectogramos -> kg
        "types": [t["type"]["name"] for t in raw["pokemontypes"]],
        "abilities": [a["ability"]["name"] for a in raw["pokemonabilities"]],
        "stats": {s["stat"]["name"].replace("-", "_"): s["base_stat"] for s in raw["pokemonstats"]},
        "sprite": config.SPRITE_URL.format(id=raw["id"]),
    }


async def fetch_pokemon_detail(name: str) -> dict | None:
    data = await _post(DETAIL_QUERY, {"name": name.strip().lower()})
    rows = data["pokemon"]
    return _to_detail(rows[0]) if rows else None

INDEX_QUERY = """
query PokemonIndex {
  pokemon(where: {is_default: {_eq: true}}, order_by: {id: asc}) {
    id
    name
    pokemontypes(order_by: {slot: asc}) { type { name } }
  }
}
"""


async def fetch_index() -> list[dict]:
    data = await _post(INDEX_QUERY, {})
    return [
        {"id": p["id"], "name": p["name"], "types": [t["type"]["name"] for t in p["pokemontypes"]]}
        for p in data["pokemon"]
    ]