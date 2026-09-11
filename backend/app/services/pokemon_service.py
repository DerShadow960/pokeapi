import logging
import re

from app import config
from app.db import repository as repo
from app.services import pokeapi

log = logging.getLogger(__name__)


class UserError(Exception):
    """Error con mensaje pensado para el usuario; es el único que llega tal cual al frontend."""


# ---------- Utilidades ----------

def normalize_official(name: str) -> str:
    """'Mr. Mime' -> 'mr-mime', "Farfetch'd" -> 'farfetchd': el formato de nombres de PokéAPI."""
    name = re.sub(r"[.'’]", "", name.strip().lower())
    return re.sub(r"\s+", "-", name)


def _display(name: str) -> str:
    return name[:1].upper() + name[1:]


def _clean_name(name: str | None) -> str:
    name = (name or "").strip()
    if len(name) > config.NAME_MAX:
        raise UserError(f"El nombre no puede pasar de {config.NAME_MAX} caracteres.")
    return name


# ---------- Mercado: Pokémon oficiales ----------

async def ensure_index() -> None:
    if repo.count_pokemon() > 0:
        return
    try:
        repo.save_index(await pokeapi.fetch_index())
    except pokeapi.PokeAPIError as exc:
        log.warning("No se pudo descargar el índice: %s", exc)
        raise UserError("PokéAPI no responde y el catálogo aún no está descargado. Intenta en unos minutos.")


async def search_pokemon(term: str, limit: int, offset: int) -> list[dict]:
    await ensure_index()
    limit = max(1, min(limit, 50))
    offset = max(0, offset)
    return repo.search_pokemon(normalize_official(term), limit, offset)


async def get_pokemon_detail(name: str) -> dict | None:
    name = normalize_official(name)
    row = repo.get_pokemon(name)
    if row and row["detail"]:
        return {**row["detail"], "bag_item_id": row["bag_item_id"]}
    if row is None and repo.count_pokemon() > 0:
        return None  # el índice está completo: si no está ahí, no existe
    try:
        detail = await pokeapi.fetch_pokemon_detail(name)
    except pokeapi.PokeAPIError as exc:
        log.warning("Detalle de %s no disponible: %s", name, exc)
        raise UserError("PokéAPI no responde y este Pokémon aún no está guardado. Intenta en unos minutos.")
    if detail is None:
        return None
    repo.save_detail(detail)
    return {**detail, "bag_item_id": row["bag_item_id"] if row else None}


# ---------- Bolsa ----------

def list_bag(term: str) -> list[dict]:
    return repo.list_bag(term.strip())


def get_bag_item(bag_item_id: int) -> dict:
    item = repo.get_bag_item(bag_item_id)
    if item is None:
        raise UserError("Ese Pokémon no está en tu bolsa.")
    return item


async def obtain_pokemon(pokemon_id: int) -> dict:
    row = repo.get_pokemon(pokemon_id)
    if row is None:
        raise UserError("Ese Pokémon no existe.")
    if row["bag_item_id"] is not None:
        raise UserError(f"{_display(row['name'])} ya está en tu bolsa.")
    if row["detail"] is None:
        await get_pokemon_detail(row["name"])  # guarda sus stats para no depender de la API después
    return repo.get_bag_item(repo.add_to_bag(pokemon_id))


def release_bag_item(bag_item_id: int) -> bool:
    if not repo.release_bag_item(bag_item_id):
        raise UserError("Ese Pokémon ya no está en tu bolsa.")
    return True


# ---------- Pokémon personalizados ----------

def _validate_custom_name(name: str, exclude_id: int | None = None) -> None:
    if repo.get_pokemon(normalize_official(name)):
        raise UserError(f"«{name}» es el nombre de un Pokémon oficial. Elige otro.")
    if repo.custom_name_taken(name, exclude_id):
        raise UserError(f"Ya tienes un Pokémon llamado «{name}».")


def _validate_size(height: float, weight: float) -> None:
    if height <= 0 or weight <= 0:
        raise UserError("La altura y el peso deben ser mayores que 0.")


def _default_custom_name() -> str:
    n = 1
    while repo.custom_name_taken(f"{config.CUSTOM_DEFAULT_NAME} {n}"):
        n += 1
    return f"{config.CUSTOM_DEFAULT_NAME} {n}"


async def create_custom(data: dict) -> dict:
    data = dict(data)
    await ensure_index()  # sin la lista de oficiales no se puede validar el nombre
    if data["type1"] not in config.TYPES or (data["type2"] and data["type2"] not in config.TYPES):
        raise UserError("Tipo de Pokémon no válido.")
    if data["type2"] == data["type1"]:
        raise UserError("Los dos tipos deben ser distintos.")
    data["type2"] = data["type2"] or None
    for stat in repo.STAT_FIELDS:
        if not config.STAT_MIN <= data[stat] <= config.STAT_MAX:
            raise UserError(f"Las estadísticas van de {config.STAT_MIN} a {config.STAT_MAX}.")
    _validate_size(data["height"], data["weight"])

    name = _clean_name(data["name"])
    if name:
        _validate_custom_name(name)
    data["name"] = name or _default_custom_name()
    return repo.get_bag_item(repo.create_custom(data))


async def update_custom(bag_item_id: int, name: str, height: float, weight: float) -> dict:
    item = get_bag_item(bag_item_id)
    if item["source"] != "custom":
        raise UserError("Solo puedes editar tus Pokémon personalizados.")
    await ensure_index()
    name = _clean_name(name)
    if not name:
        raise UserError("El nombre no puede quedar vacío.")
    _validate_custom_name(name, exclude_id=item["id"])
    _validate_size(height, weight)
    repo.update_custom(item["id"], name, height, weight)
    return repo.get_bag_item(bag_item_id)


# ---------- Equipos ----------

def list_teams() -> list[dict]:
    return repo.list_teams()


def get_team(team_id: int) -> dict:
    team = next((t for t in repo.list_teams() if t["id"] == team_id), None)
    if team is None:
        raise UserError("Ese equipo no existe.")
    return team


def rename_team(team_id: int, name: str) -> dict:
    get_team(team_id)
    name = _clean_name(name)
    if not name:
        raise UserError("El nombre del equipo no puede quedar vacío.")
    repo.rename_team(team_id, name)
    return get_team(team_id)


def set_team_color(team_id: int, color: str) -> dict:
    get_team(team_id)
    if color not in config.TEAM_COLORS:
        raise UserError("Ese color no está en la paleta.")
    repo.set_team_color(team_id, color)
    return get_team(team_id)


def disband_team(team_id: int) -> dict:
    get_team(team_id)
    repo.clear_team(team_id)
    return get_team(team_id)


def add_member(team_id: int, bag_item_id: int) -> dict:
    team = get_team(team_id)
    if len(team["members"]) >= config.TEAM_SIZE:
        raise UserError(f"{team['name']} ya tiene {config.TEAM_SIZE} Pokémon.")
    item = get_bag_item(bag_item_id)
    if repo.is_in_team(team_id, bag_item_id):
        raise UserError(f"{_display(item['name'])} ya está en {team['name']}.")
    repo.add_member(team_id, bag_item_id)
    return get_team(team_id)


def remove_member(team_id: int, member_id: int) -> dict:
    if not repo.remove_member(team_id, member_id):
        raise UserError("Ese Pokémon ya no está en el equipo.")
    return get_team(team_id)