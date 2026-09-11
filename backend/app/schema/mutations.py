from dataclasses import asdict

import strawberry

from app.schema.types import BagItem, CustomPokemonInput, CustomPokemonUpdateInput, Team
from app.services import pokemon_service as service


@strawberry.type
class Mutation:
    # ---------- Bolsa ----------
    @strawberry.mutation(description="Pasa un Pokémon oficial del mercado a tu bolsa.")
    async def obtain_pokemon(self, pokemon_id: int) -> BagItem:
        return BagItem.from_dict(await service.obtain_pokemon(pokemon_id))

    @strawberry.mutation(description="Oficial: sale de la bolsa. Personalizado: se borra. Sale de sus equipos.")
    def release_bag_item(self, id: int) -> bool:
        return service.release_bag_item(id)

    @strawberry.mutation
    async def create_custom_pokemon(self, input: CustomPokemonInput) -> BagItem:
        return BagItem.from_dict(await service.create_custom(asdict(input)))

    @strawberry.mutation(description="'id' es el id en la bolsa. Solo se editan nombre, altura y peso.")
    async def update_custom_pokemon(self, id: int, input: CustomPokemonUpdateInput) -> BagItem:
        return BagItem.from_dict(await service.update_custom(id, input.name, input.height, input.weight))

    # ---------- Equipos ----------
    @strawberry.mutation
    def rename_team(self, id: int, name: str) -> Team:
        return Team.from_dict(service.rename_team(id, name))

    @strawberry.mutation
    def set_team_color(self, id: int, color: str) -> Team:
        return Team.from_dict(service.set_team_color(id, color))

    @strawberry.mutation
    def disband_team(self, id: int) -> Team:
        return Team.from_dict(service.disband_team(id))

    @strawberry.mutation
    def add_team_member(self, team_id: int, bag_item_id: int) -> Team:
        return Team.from_dict(service.add_member(team_id, bag_item_id))

    @strawberry.mutation
    def remove_team_member(self, team_id: int, member_id: int) -> Team:
        return Team.from_dict(service.remove_member(team_id, member_id))