from app.db import repository as repo
from app.services import pokeapi
from app.services import pokemon_service as service
from app.services.pokemon_service import UserError
from tests.helpers import DBTestCase, custom_data, detail


class TestMarket(DBTestCase):
    async def test_search_normalizes_official_names(self):
        self.assertEqual([p["name"] for p in await service.search_pokemon("Mr. Mime", 10, 0)], ["mr-mime"])
        self.assertEqual(len(await service.search_pokemon("char", 10, 0)), 2)

    async def test_cached_detail_does_not_call_api(self):
        repo.save_detail(detail(4, "charmander", ["fire"]))
        await service.get_pokemon_detail("charmander")
        self.fetch_detail.assert_not_called()

    async def test_unknown_name_does_not_call_api(self):
        self.assertIsNone(await service.get_pokemon_detail("fakemon"))
        self.fetch_detail.assert_not_called()

    async def test_detail_with_api_down_is_user_error(self):
        self.fetch_detail.side_effect = pokeapi.PokeAPIError("down")
        with self.assertRaises(UserError), self.assertLogs("app.services.pokemon_service", "WARNING"):
            await service.get_pokemon_detail("charmander")


class TestBag(DBTestCase):
    async def test_obtain_caches_detail_and_rejects_duplicates(self):
        item = await service.obtain_pokemon(4)
        self.assertEqual((item["name"], item["stats"]["hp"]), ("charmander", 40))
        self.assertIsNotNone(repo.get_pokemon(4)["detail"])
        with self.assertRaisesRegex(UserError, "ya está en tu bolsa"):
            await service.obtain_pokemon(4)

    async def test_bag_keeps_insertion_order_mixing_sources(self):
        await service.obtain_pokemon(4)
        await service.create_custom(custom_data(name="Fueguito"))
        self.assertEqual([i["name"] for i in service.list_bag("")], ["charmander", "Fueguito"])


class TestCustoms(DBTestCase):
    async def test_default_names_are_sequential(self):
        a = await service.create_custom(custom_data())
        b = await service.create_custom(custom_data())
        self.assertEqual((a["name"], b["name"]), ("PokePersonalizado 1", "PokePersonalizado 2"))

    async def test_rejects_official_and_repeated_names(self):
        await service.create_custom(custom_data(name="Fueguito"))
        for name in ("Charmander", "Mr Mime", "FUEGUITO"):
            with self.subTest(name), self.assertRaises(UserError):
                await service.create_custom(custom_data(name=name))
        await service.create_custom(custom_data(name="Fueguito 1"))  # distinto: permitido

    async def test_stats_and_types_are_validated(self):
        for bad in (custom_data(hp=151), custom_data(hp=0), custom_data(type1="lava"), custom_data(type2="fire")):
            with self.subTest(bad), self.assertRaises(UserError):
                await service.create_custom(bad)

    async def test_only_customs_can_be_edited(self):
        official = await service.obtain_pokemon(4)
        with self.assertRaises(UserError):
            await service.update_custom(official["bag_item_id"], "Otro", 1, 1)
        mine = await service.create_custom(custom_data(name="Fueguito"))
        edited = await service.update_custom(mine["bag_item_id"], "Fueguito", 1.2, 9)  # su propio nombre: permitido
        self.assertEqual(edited["height"], 1.2)


class TestTeams(DBTestCase):
    async def asyncSetUp(self):
        self.charm = (await service.obtain_pokemon(4))["bag_item_id"]
        self.custom = (await service.create_custom(custom_data(name="Fueguito")))["bag_item_id"]

    def test_three_fixed_teams_with_default_colors(self):
        teams = service.list_teams()
        self.assertEqual([(t["name"], t["color"]) for t in teams], [("E1", "red"), ("E2", "black"), ("E3", "white")])

    def test_only_bag_items_no_duplicates_max_six(self):
        with self.assertRaisesRegex(UserError, "no está en tu bolsa"):
            service.add_member(1, 999)
        service.add_member(1, self.charm)
        with self.assertRaisesRegex(UserError, "ya está en E1"):
            service.add_member(1, self.charm)
        service.add_member(2, self.charm)  # el mismo Pokémon en otro equipo: permitido

    async def test_team_limit(self):
        for pid in (1, 5, 122):
            service.add_member(1, (await service.obtain_pokemon(pid))["bag_item_id"])
        service.add_member(1, self.charm)
        service.add_member(1, self.custom)
        extra = (await service.create_custom(custom_data()))["bag_item_id"]
        service.add_member(1, extra)
        self.assertEqual(len(service.get_team(1)["members"]), 6)
        with self.assertRaisesRegex(UserError, "ya tiene 6"):
            service.add_member(1, (await service.create_custom(custom_data()))["bag_item_id"])

    def test_disband_empties_but_keeps_team(self):
        service.add_member(1, self.charm)
        team = service.disband_team(1)
        self.assertEqual((team["name"], team["members"]), ("E1", []))

    def test_release_removes_from_teams(self):
        service.add_member(1, self.charm)
        service.add_member(2, self.custom)
        service.release_bag_item(self.charm)   # oficial: vuelve al mercado
        service.release_bag_item(self.custom)  # personalizado: se borra
        self.assertEqual([t["members"] for t in service.list_teams()], [[], [], []])
        self.assertIsNotNone(repo.get_pokemon(4))
        self.assertEqual(service.list_bag(""), [])

    def test_color_must_be_in_palette(self):
        self.assertEqual(service.set_team_color(1, "blue")["color"], "blue")
        with self.assertRaises(UserError):
            service.set_team_color(1, "#123456")