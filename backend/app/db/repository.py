import json
from contextlib import contextmanager

from app.db.database import get_connection

STAT_FIELDS = ("hp", "attack", "defense", "special_attack", "special_defense", "speed")


@contextmanager
def _db():
    conn = get_connection()
    try:
        with conn:  # commit si todo sale bien, rollback si hay excepción
            yield conn
    finally:
        conn.close()


# ---------- Pokémon oficiales: índice + caché (el "mercado") ----------

_POKEMON_SELECT = "SELECT p.*, b.id AS bag_item_id FROM pokemon p LEFT JOIN bag_item b ON b.pokemon_id = p.id"


def _pokemon(row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "types": json.loads(row["types"]),
        "detail": json.loads(row["detail"]) if row["detail"] else None,
        "bag_item_id": row["bag_item_id"],
    }


def count_pokemon() -> int:
    with _db() as conn:
        return conn.execute("SELECT COUNT(*) FROM pokemon").fetchone()[0]


def save_index(rows: list[dict]) -> None:
    with _db() as conn:
        conn.executemany(
            "INSERT OR IGNORE INTO pokemon (id, name, types) VALUES (?, ?, ?)",
            [(r["id"], r["name"], json.dumps(r["types"])) for r in rows],
        )


def search_pokemon(term: str, limit: int, offset: int) -> list[dict]:
    with _db() as conn:
        rows = conn.execute(
            _POKEMON_SELECT + " WHERE instr(p.name, ?) > 0 ORDER BY p.id LIMIT ? OFFSET ?",
            (term, limit, offset),
        ).fetchall()
    return [_pokemon(r) for r in rows]


def get_pokemon(key: int | str) -> dict | None:
    column = "p.id" if isinstance(key, int) else "p.name"
    with _db() as conn:
        row = conn.execute(f"{_POKEMON_SELECT} WHERE {column} = ?", (key,)).fetchone()
    return _pokemon(row) if row else None


def save_detail(detail: dict) -> None:
    with _db() as conn:
        conn.execute(
            """INSERT INTO pokemon (id, name, types, detail) VALUES (?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET detail = excluded.detail""",
            (detail["id"], detail["name"], json.dumps(detail["types"]), json.dumps(detail)),
        )


# ---------- Bolsa: oficiales obtenidos + personalizados ----------

_BAG_COLUMNS = """
    b.id AS bag_item_id,
    p.id AS api_id, p.name AS api_name, p.types AS api_types, p.detail AS api_detail,
    c.id AS custom_id, c.name AS custom_name, c.type1, c.type2, c.height, c.weight,
    c.hp, c.attack, c.defense, c.special_attack, c.special_defense, c.speed,
    (SELECT COUNT(*) FROM team_member tm WHERE tm.bag_item_id = b.id) AS team_count
"""
_BAG_JOINS = """
    LEFT JOIN pokemon p ON p.id = b.pokemon_id
    LEFT JOIN custom_pokemon c ON c.id = b.custom_pokemon_id
"""


def _bag_item(row) -> dict:
    """Misma forma para oficiales y personalizados: el resto del sistema no distingue el origen."""
    if row["api_id"] is not None:
        detail = json.loads(row["api_detail"]) if row["api_detail"] else {}
        return {
            "bag_item_id": row["bag_item_id"], "source": "api", "id": row["api_id"], "name": row["api_name"],
            "types": json.loads(row["api_types"]), "height": detail.get("height"), "weight": detail.get("weight"),
            "abilities": detail.get("abilities", []), "stats": detail.get("stats", {}), "team_count": row["team_count"],
        }
    return {
        "bag_item_id": row["bag_item_id"], "source": "custom", "id": row["custom_id"], "name": row["custom_name"],
        "types": [t for t in (row["type1"], row["type2"]) if t], "height": row["height"], "weight": row["weight"],
        "abilities": [], "stats": {f: row[f] for f in STAT_FIELDS}, "team_count": row["team_count"],
    }


def list_bag(term: str = "") -> list[dict]:
    with _db() as conn:
        rows = conn.execute(
            f"""SELECT {_BAG_COLUMNS} FROM bag_item b {_BAG_JOINS}
                WHERE instr(lower(coalesce(p.name, c.name)), lower(?)) > 0 ORDER BY b.id""",
            (term,),
        ).fetchall()
    return [_bag_item(r) for r in rows]


def get_bag_item(bag_item_id: int) -> dict | None:
    with _db() as conn:
        row = conn.execute(
            f"SELECT {_BAG_COLUMNS} FROM bag_item b {_BAG_JOINS} WHERE b.id = ?", (bag_item_id,)
        ).fetchone()
    return _bag_item(row) if row else None


def add_to_bag(pokemon_id: int) -> int:
    with _db() as conn:
        return conn.execute("INSERT INTO bag_item (pokemon_id) VALUES (?)", (pokemon_id,)).lastrowid


def release_bag_item(bag_item_id: int) -> bool:
    """Oficial: sale de la bolsa (sigue en el mercado). Personalizado: se borra para siempre.
    En ambos casos ON DELETE CASCADE lo quita de los equipos."""
    with _db() as conn:
        row = conn.execute("SELECT custom_pokemon_id FROM bag_item WHERE id = ?", (bag_item_id,)).fetchone()
        if row is None:
            return False
        if row["custom_pokemon_id"] is not None:
            conn.execute("DELETE FROM custom_pokemon WHERE id = ?", (row["custom_pokemon_id"],))
        else:
            conn.execute("DELETE FROM bag_item WHERE id = ?", (bag_item_id,))
        return True


# ---------- Pokémon personalizados ----------

def create_custom(data: dict) -> int:
    """Crea el personalizado y lo mete a la bolsa en la misma transacción. Regresa el id en la bolsa."""
    with _db() as conn:
        custom_id = conn.execute(
            """INSERT INTO custom_pokemon
               (name, type1, type2, hp, attack, defense, special_attack, special_defense, speed, height, weight)
               VALUES (:name, :type1, :type2, :hp, :attack, :defense, :special_attack,
                       :special_defense, :speed, :height, :weight)""",
            data,
        ).lastrowid
        return conn.execute("INSERT INTO bag_item (custom_pokemon_id) VALUES (?)", (custom_id,)).lastrowid


def custom_name_taken(name: str, exclude_id: int | None = None) -> bool:
    with _db() as conn:
        row = conn.execute(
            "SELECT 1 FROM custom_pokemon WHERE name = ? AND id IS NOT ?", (name, exclude_id)
        ).fetchone()
    return row is not None


def update_custom(custom_id: int, name: str, height: float, weight: float) -> bool:
    with _db() as conn:
        cur = conn.execute(
            "UPDATE custom_pokemon SET name = ?, height = ?, weight = ? WHERE id = ?",
            (name, height, weight, custom_id),
        )
        return cur.rowcount > 0


# ---------- Equipos ----------

def rename_team(team_id: int, name: str) -> bool:
    with _db() as conn:
        return conn.execute("UPDATE team SET name = ? WHERE id = ?", (name, team_id)).rowcount > 0


def set_team_color(team_id: int, color: str) -> bool:
    with _db() as conn:
        return conn.execute("UPDATE team SET color = ? WHERE id = ?", (color, team_id)).rowcount > 0


def list_teams() -> list[dict]:
    with _db() as conn:
        teams = conn.execute("SELECT * FROM team ORDER BY id").fetchall()
        members = conn.execute(
            f"""SELECT tm.id AS member_id, tm.team_id, {_BAG_COLUMNS}
                FROM team_member tm JOIN bag_item b ON b.id = tm.bag_item_id {_BAG_JOINS}
                ORDER BY tm.id"""
        ).fetchall()
    result = {t["id"]: {"id": t["id"], "name": t["name"], "color": t["color"], "members": []} for t in teams}
    for m in members:
        result[m["team_id"]]["members"].append({"member_id": m["member_id"], "item": _bag_item(m)})
    return list(result.values())


def is_in_team(team_id: int, bag_item_id: int) -> bool:
    with _db() as conn:
        row = conn.execute(
            "SELECT 1 FROM team_member WHERE team_id = ? AND bag_item_id = ?", (team_id, bag_item_id)
        ).fetchone()
    return row is not None


def add_member(team_id: int, bag_item_id: int) -> int:
    with _db() as conn:
        return conn.execute(
            "INSERT INTO team_member (team_id, bag_item_id) VALUES (?, ?)", (team_id, bag_item_id)
        ).lastrowid


def remove_member(team_id: int, member_id: int) -> bool:
    with _db() as conn:
        cur = conn.execute("DELETE FROM team_member WHERE id = ? AND team_id = ?", (member_id, team_id))
        return cur.rowcount > 0


def clear_team(team_id: int) -> None:
    with _db() as conn:
        conn.execute("DELETE FROM team_member WHERE team_id = ?", (team_id,))