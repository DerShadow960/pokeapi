from enum import Enum

import strawberry

from app import config


def sprite_url(pokemon_id: int) -> str:
    return config.SPRITE_URL.format(id=pokemon_id)


@strawberry.type
class Stats:
    hp: int
    attack: int
    defense: int
    special_attack: int
    special_defense: int
    speed: int

    @classmethod
    def from_dict(cls, d: dict) -> "Stats":
        return cls(**{f: d.get(f, 0) for f in ("hp", "attack", "defense", "special_attack", "special_defense", "speed")})


@strawberry.type(description="Pokémon oficial en el mercado. bagItemId es null si no lo tienes.")
class PokemonSummary:
    id: int
    name: str
    types: list[str]
    sprite: str
    bag_item_id: int | None

    @classmethod
    def from_dict(cls, d: dict) -> "PokemonSummary":
        return cls(id=d["id"], name=d["name"], types=d["types"], sprite=sprite_url(d["id"]), bag_item_id=d["bag_item_id"])


@strawberry.type
class PokemonDetail:
    id: int
    name: str
    types: list[str]
    sprite: str
    height: float
    weight: float
    abilities: list[str]
    stats: Stats
    bag_item_id: int | None

    @classmethod
    def from_dict(cls, d: dict) -> "PokemonDetail":
        return cls(
            id=d["id"], name=d["name"], types=d["types"], sprite=sprite_url(d["id"]), height=d["height"],
            weight=d["weight"], abilities=d["abilities"], stats=Stats.from_dict(d["stats"]), bag_item_id=d["bag_item_id"],
        )


@strawberry.enum
class Source(Enum):
    API = "api"
    CUSTOM = "custom"


@strawberry.type(description="Pokémon en tu bolsa: oficial obtenido o personalizado.")
class BagItem:
    id: int
    source: Source
    pokemon_id: int
    name: str
    types: list[str]
    sprite: str | None
    height: float | None
    weight: float | None
    abilities: list[str]
    stats: Stats
    team_count: int

    @classmethod
    def from_dict(cls, d: dict) -> "BagItem":
        is_api = d["source"] == "api"
        return cls(
            id=d["bag_item_id"], source=Source(d["source"]), pokemon_id=d["id"], name=d["name"], types=d["types"],
            sprite=sprite_url(d["id"]) if is_api else None, height=d["height"], weight=d["weight"],
            abilities=d["abilities"], stats=Stats.from_dict(d["stats"]), team_count=d["team_count"],
        )


@strawberry.enum
class TeamStatus(Enum):
    INACTIVE = "inactive"
    INCOMPLETE = "incomplete"
    COMPLETE = "complete"


@strawberry.type
class TeamMember:
    member_id: int
    pokemon: BagItem


@strawberry.type
class Team:
    id: int
    name: str
    color: str
    members: list[TeamMember]

    @strawberry.field
    def size(self) -> int:
        return len(self.members)

    @strawberry.field
    def status(self) -> TeamStatus:
        if not self.members:
            return TeamStatus.INACTIVE
        return TeamStatus.COMPLETE if len(self.members) >= config.TEAM_SIZE else TeamStatus.INCOMPLETE

    @classmethod
    def from_dict(cls, d: dict) -> "Team":
        members = [TeamMember(member_id=m["member_id"], pokemon=BagItem.from_dict(m["item"])) for m in d["members"]]
        return cls(id=d["id"], name=d["name"], color=d["color"], members=members)


@strawberry.input
class CustomPokemonInput:
    name: str | None = None
    type1: str
    type2: str | None = None
    hp: int
    attack: int
    defense: int
    special_attack: int
    special_defense: int
    speed: int
    height: float
    weight: float


@strawberry.input
class CustomPokemonUpdateInput:
    name: str
    height: float
    weight: float