import os

POKEAPI_URL = os.getenv("POKEAPI_URL", "https://graphql.pokeapi.co/v1beta2")
POKEAPI_TIMEOUT = float(os.getenv("POKEAPI_TIMEOUT", "8"))
DB_PATH = os.getenv("DB_PATH", "pokedopamina.db")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5500,http://127.0.0.1:5500").split(",")
SPRITE_URL = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/{id}.png"

TEAM_SIZE = 6
STAT_MIN = 1
STAT_MAX = 150
NAME_MAX = 30
CUSTOM_DEFAULT_NAME = "PokePersonalizado"
TYPES = (
    "normal", "fire", "water", "electric", "grass", "ice", "fighting", "poison", "ground",
    "flying", "psychic", "bug", "rock", "ghost", "dragon", "dark", "steel", "fairy",
)
TEAM_COLORS = ("red", "black", "white", "blue", "green", "yellow", "purple", "orange")
TEAM_DEFAULT_COLORS = ("red", "black", "white")