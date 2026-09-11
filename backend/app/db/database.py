import sqlite3

from app import config

STAT = f"INTEGER NOT NULL CHECK ({{col}} BETWEEN {config.STAT_MIN} AND {config.STAT_MAX})"
COLORS = ", ".join(f"'{c}'" for c in config.TEAM_COLORS)

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS pokemon (
    id     INTEGER PRIMARY KEY,
    name   TEXT NOT NULL UNIQUE,
    types  TEXT NOT NULL,
    detail TEXT
);

CREATE TABLE IF NOT EXISTS custom_pokemon (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL UNIQUE COLLATE NOCASE,
    type1           TEXT NOT NULL,
    type2           TEXT CHECK (type2 IS NULL OR type2 <> type1),
    hp              {STAT.format(col="hp")},
    attack          {STAT.format(col="attack")},
    defense         {STAT.format(col="defense")},
    special_attack  {STAT.format(col="special_attack")},
    special_defense {STAT.format(col="special_defense")},
    speed           {STAT.format(col="speed")},
    height          REAL NOT NULL CHECK (height > 0),
    weight          REAL NOT NULL CHECK (weight > 0)
);

CREATE TABLE IF NOT EXISTS bag_item (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    pokemon_id        INTEGER UNIQUE REFERENCES pokemon(id),
    custom_pokemon_id INTEGER UNIQUE REFERENCES custom_pokemon(id) ON DELETE CASCADE,
    CHECK ((pokemon_id IS NULL) <> (custom_pokemon_id IS NULL))
);

CREATE TABLE IF NOT EXISTS team (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    name  TEXT NOT NULL,
    color TEXT NOT NULL CHECK (color IN ({COLORS}))
);

CREATE TABLE IF NOT EXISTS team_member (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id     INTEGER NOT NULL REFERENCES team(id) ON DELETE CASCADE,
    bag_item_id INTEGER NOT NULL REFERENCES bag_item(id) ON DELETE CASCADE,
    UNIQUE (team_id, bag_item_id)
);
"""


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    conn = get_connection()
    try:
        conn.executescript(SCHEMA)
        with conn:
            if conn.execute("SELECT COUNT(*) FROM team").fetchone()[0] == 0:
                conn.executemany(
                    "INSERT INTO team (name, color) VALUES (?, ?)",
                    [(f"E{n}", color) for n, color in enumerate(config.TEAM_DEFAULT_COLORS, start=1)],
                )
    finally:
        conn.close()