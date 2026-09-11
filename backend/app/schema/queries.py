import strawberry

from app import config
from app.schema.types import BagItem, PokemonDetail, PokemonSummary, Team
from app.services import pokemon_service as service


@strawberry.type
class Query:
    @strawberry.field(description="Mercado: Pokémon oficiales. Sin 'search' funciona como explorar.")
    async def pokemons(self, search: str = "", limit: int = 24, offset: int = 0) -> list[PokemonSummary]:
        return [PokemonSummary.from_dict(p) for p in await service.search_pokemon(search, limit, offset)]

    @strawberry.field(description="Detalle de un Pokémon oficial; null si no existe.")
    async def pokemon(self, name: str) -> PokemonDetail | None:
        detail = await service.get_pokemon_detail(name)
        return PokemonDetail.from_dict(detail) if detail else None

    @strawberry.field(description="Tu bolsa: oficiales obtenidos y personalizados, en orden de agregado.")
    def bag(self, search: str = "") -> list[BagItem]:
        return [BagItem.from_dict(i) for i in service.list_bag(search)]

    @strawberry.field
    def teams(self) -> list[Team]:
        return [Team.from_dict(t) for t in service.list_teams()]

    @strawberry.field(description="Paleta de colores permitida para los equipos.")
    def team_colors(self) -> list[str]:
        return list(config.TEAM_COLORS)