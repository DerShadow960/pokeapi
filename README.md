# Poké Explorer

Full-stack app to explore Pokémon, keep them in a personal bag, and build up to 3 teams.
Python backend with its own GraphQL API, framework-free HTML/CSS/JS frontend, data persisted in SQLite.

> The user interface and user-facing error messages are in Spanish.

- **Frontend:** https://frontend-lemon-two-84.vercel.app
- **Backend (GraphQL + GraphiQL console):** https://pokeapi-production-ecf5.up.railway.app/graphql

## Features

- **Explore (market):** browse and search the 1025 official Pokémon, view their details (types, height, weight, abilities, and stats), and **obtain** them for your bag.
- **My Pokémon (bag):** the official Pokémon you obtained plus your **custom Pokémon**, in the order they were added, with a search box.
  - Create custom Pokémon with a name, one or two types, 6 stats (1 to 150), height, and weight.
  - If no name is given, it is called `PokePersonalizado N`.
  - Official Pokémon names and duplicate names (case-insensitive) are rejected.
  - Only a custom Pokémon's name, height, and weight can be edited.
  - Releasing an official Pokémon returns it to the market; deleting a custom one removes it. Both ask for confirmation.
- **Teams:** 3 fixed teams (E1, E2, E3).
  - Up to 6 Pokémon each, only from your bag, with no duplicates within a team (the same Pokémon can be in all 3).
  - Teams can be renamed, recolored (8-color palette), and disbanded (emptied, not deleted).
  - Collapsed card: the first member's image plus each member's name, type, and HP. Expanded: full details.
- **UI:** responsive, with loading, empty, and error states in every view.

## Architecture

```
Browser ─► Frontend (HTML/CSS/JS) ─► POST /graphql ─► Strawberry (Python)
                                                        │
                                         pokemon_service (business rules)
                                            │                     │
                                   repository (SQL)      pokeapi (httpx client)
                                            │                     │
                                         SQLite          PokéAPI GraphQL v1beta2
```

The frontend **never** calls PokéAPI: all data goes through our own GraphQL API. Official artwork is loaded from PokéAPI's public sprites repository on GitHub; those are static files, not data calls.

```
backend/
  app/
    main.py              # ASGI app: Strawberry + CORS + startup
    config.py            # settings and rules (limits, types, palette)
    schema/              # GraphQL types, queries, and mutations
    services/
      pokeapi.py         # GraphQL client for PokéAPI
      pokemon_service.py # business rules
    db/
      database.py        # SQLite schema and creation of the 3 teams
      repository.py      # all SQL queries
  tests/
frontend/
  index.html  css/styles.css  js/api.js  js/app.js
```

## How to run it

Requirements: Python 3.10 or newer (tested with 3.12 and 3.14).

**Backend**

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # fish: source .venv/bin/activate.fish
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

On startup it creates the database and downloads the Pokémon catalog with a single PokéAPI call. The GraphiQL console is available at http://localhost:8000/graphql.

**Frontend** (in another terminal)

```bash
cd frontend
python -m http.server 5500
```

Open http://localhost:5500. It must be served over HTTP (not opened as a file) because the JS uses ES modules.

**Tests**

```bash
cd backend
source .venv/bin/activate
python -m unittest -v
```

**Environment variables (backend)**

| Variable | Default | Purpose |
|---|---|---|
| `POKEAPI_URL` | `https://graphql.pokeapi.co/v1beta2` | PokéAPI endpoint |
| `POKEAPI_TIMEOUT` | `8` | Seconds before PokéAPI is considered down |
| `DB_PATH` | `pokedopamina.db` | SQLite file path |
| `CORS_ORIGINS` | `http://localhost:5500,http://127.0.0.1:5500` | Allowed origins, comma-separated |

The backend URL used by the frontend is set in `frontend/js/api.js` (`API_URL`).

## Tech choices

| Piece | Choice | Why |
|---|---|---|
| API | **Strawberry** (GraphQL) | Schema defined with Python classes and type hints: the code is the documentation. |
| Server | **uvicorn** + Starlette | Starlette already ships with Strawberry's ASGI integration; it provides startup hooks and CORS with no extra dependencies. |
| PokéAPI client | **httpx** | Async with explicit timeouts, key to detecting when PokéAPI is down. |
| Database | **SQLite** via `sqlite3` (no ORM) | Zero setup, explicit SQL, and real constraints enforced in the database. |
| Frontend | **Vanilla HTML, CSS, and JS** | No build step. ES modules, `<template>`, and native `<dialog>`/`<details>`. |
| Tests | **unittest** | Ships with Python; no extra dependencies. |

The backend has only 3 direct dependencies: `strawberry-graphql[asgi]`, `uvicorn`, and `httpx`.

## GraphQL design

**Queries:** `pokemons(search, limit, offset)`, `pokemon(name)`, `bag(search)`, `teams`, `teamColors`.
**Mutations:** `obtainPokemon`, `releaseBagItem`, `createCustomPokemon`, `updateCustomPokemon`, `renameTeam`, `setTeamColor`, `disbandTeam`, `addTeamMember`, `removeTeamMember`.

- **`BagItem`** represents an obtained official Pokémon and a custom one the same way (`source: API | CUSTOM`), so the bag and teams never need to care about the origin.
- **Composition:** a `TeamMember` contains a `BagItem` (`members { pokemon { name stats { hp } } }`), with no duplicated fields.
- **`Team.status`** (`INACTIVE`, `INCOMPLETE`, `COMPLETE`) is computed on the server, so the rule lives in one place.
- **`pokemons` exposes `bagItemId`** (`null` if you don't own it), so the market knows what is already in your bag.
- **The update input only accepts name, height, and weight:** the rule about what is editable is part of the contract.
- **The frontend uses fragments** (`BagFields`, `TeamFields`) and loads the bag, teams, and palette in **a single request**.

Example for GraphiQL:

```graphql
query {
  pokemons(search: "char", limit: 3) { id name types bagItemId }
  teams { name color status members { pokemon { name stats { hp } } } }
}
```

## Persistence

Everything is stored server-side in SQLite; nothing relies on `localStorage` or in-memory data. The bag and teams are shared (the challenge does not require authentication).

| Table | Contents |
|---|---|
| `pokemon` | Index of official Pokémon (id, name, types) plus their details as JSON once requested |
| `custom_pokemon` | Custom Pokémon, with each stat in its own column |
| `bag_item` | The bag: points to an official Pokémon **or** a custom one |
| `team` | The 3 teams, with name and color |
| `team_member` | Team members; they point to `bag_item` |

Key rules are guaranteed by the database, not just by the code:

- **Only Pokémon in your bag can join a team:** `team_member` references `bag_item` through a foreign key.
- **No duplicates:** `UNIQUE` constraints for one official Pokémon per bag, one Pokémon per team, and custom names (case-insensitive).
- **Valid data:** `CHECK` constraints for stats from 1 to 150, positive height and weight, distinct types, and palette colors.
- **Cascading deletes:** deleting a custom Pokémon or releasing an official one automatically removes it from its teams.

## Caching and error handling

PokéAPI allows 100 calls per hour per IP and restarts daily, so the database also works as a cache:

- **Local index:** on startup, all official Pokémon are downloaded in **a single call**. Browsing and searching run against SQLite and cost no API calls.
- **Details:** each Pokémon's details are requested from PokéAPI only once, then stored. A name that is not in the index is answered as "not found" without calling the API.
- **Obtaining a Pokémon stores its details,** so the bag and teams render fully even if PokéAPI is down.
- **If PokéAPI is down at startup,** the server starts anyway and retries on the next search.

Errors:

- **From PokéAPI:** timeouts, rate limiting (429), non-JSON responses, and GraphQL errors all become a single `PokeAPIError`.
- **Business rule errors (`UserError`):** reach the user with a clear message (e.g. "E1 ya tiene 6 Pokémon") and are not logged as failures.
- **Unexpected errors:** hidden with `MaskErrors` (the client only sees a generic "internal error" message) and fully logged on the server.
- **Three validation layers:** HTML attributes (UX), service layer (clear messages), and database constraints (last line of defense).
- **Security:** parameterized SQL queries, GraphQL variables (never string concatenation), `textContent` everywhere in the frontend (no XSS), and CORS restricted to known origins.
- **Frontend:** loading, empty, and error states per view; success and error toasts; confirmation for destructive actions; if an image fails to load, the Pokémon's initial is shown over its type color.

## Testing

22 automated tests with `unittest`. Each test uses a fresh SQLite database in a temporary file and replaces PokéAPI with mocks: tests never hit the network, never consume the rate limit, and always give the same result.

- **`test_pokeapi.py`:** unit and stat-name conversion; every failure type becomes a `PokeAPIError`.
- **`test_service.py`:** all business rules against a real SQLite database (search, caching, bag, custom Pokémon, team limits, cascades, palette), which also covers the repository.
- **`test_schema.py`:** the full GraphQL schema, including error messages and masking of internal errors.

The frontend was tested manually and with an automated browser covering every flow on desktop and mobile.

## What I would improve next

- Frontend E2E tests (Playwright) and continuous integration with GitHub Actions.
- Updating only what changed on the client after a mutation, instead of refetching the whole collection.
- Typed GraphQL errors (result unions) instead of message-only errors.
- Authentication, with a bag and teams per user.
- PostgreSQL if the backend needs multiple instances (SQLite requires a persistent disk and a single instance).
- Periodically refreshing the index to include new Pokémon.
- Reordering team members and keeping view state in the URL.
- Rate limiting on our own API.


## Deployment

- **Frontend:** Vercel, served as a static site from `frontend/`.
- **Backend:** Railway, built from `backend/` and started with
  `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
  A persistent volume is mounted at `/data` (`DB_PATH=/data/pokedopamina.db`), so the SQLite
  database survives restarts and redeploys. `CORS_ORIGINS` only allows the Vercel URL.
- **Why not everything on Vercel:** its functions have a read-only, ephemeral filesystem, so SQLite
  data would be lost. Railway provides an always-on container with a real disk.