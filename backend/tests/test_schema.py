from unittest.mock import patch

from app.main import schema
from app.services import pokemon_service as service
from tests.helpers import DBTestCase


class TestSchema(DBTestCase):
    async def test_market_and_teams_in_one_request(self):
        result = await schema.execute('{ pokemons(search: "char") { name bagItemId } teams { name color status } }')
        self.assertIsNone(result.errors)
        self.assertEqual(result.data["pokemons"][0], {"name": "charmander", "bagItemId": None})
        self.assertEqual(result.data["teams"][0], {"name": "E1", "color": "red", "status": "INACTIVE"})

    async def test_user_errors_reach_the_client(self):
        result = await schema.execute('mutation { setTeamColor(id: 1, color: "pink") { id } }')
        self.assertEqual(result.errors[0].message, "Ese color no está en la paleta.")

    async def test_unexpected_errors_are_masked(self):
        with patch.object(service, "list_teams", side_effect=RuntimeError("ruta secreta /home")), \
                self.assertLogs("strawberry.execution", "ERROR"):  # el servidor sí lo registra
            result = await schema.execute("{ teams { id } }")
        self.assertEqual(result.errors[0].message, "Error interno. Intenta de nuevo.")