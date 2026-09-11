// Único archivo que habla con el backend. Todo pasa por POST /graphql.
const API_URL = "http://localhost:8000/graphql";

const BAG_FIELDS = `
  fragment BagFields on BagItem {
    id source pokemonId name types sprite height weight abilities teamCount
    stats { hp attack defense specialAttack specialDefense speed }
  }`;

const TEAM_FIELDS = `
  fragment TeamFields on Team {
    id name color size status
    members { memberId pokemon { ...BagFields } }
  }` + BAG_FIELDS;

export class ApiError extends Error {}

async function gql(query, variables = {}) {
  let response;
  try {
    response = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, variables }),
    });
  } catch {
    throw new ApiError("No se pudo conectar con el servidor. Revisa que el backend esté encendido.");
  }
  let body;
  try {
    body = await response.json();
  } catch {
    throw new ApiError(`El servidor respondió con un error (${response.status}).`);
  }
  if (body.errors?.length) throw new ApiError(body.errors[0].message);
  return body.data;
}

export const api = {
  // ---------- Mercado ----------
  searchPokemon: (search, limit, offset) =>
    gql(`query SearchPokemon($search: String!, $limit: Int!, $offset: Int!) {
      pokemons(search: $search, limit: $limit, offset: $offset) { id name types sprite bagItemId }
    }`, { search, limit, offset }).then((d) => d.pokemons),

  pokemonDetail: (name) =>
    gql(`query PokemonDetail($name: String!) {
      pokemon(name: $name) {
        id name types sprite height weight abilities bagItemId
        stats { hp attack defense specialAttack specialDefense speed }
      }
    }`, { name }).then((d) => d.pokemon),

  obtain: (pokemonId) =>
    gql(`mutation Obtain($pokemonId: Int!) { obtainPokemon(pokemonId: $pokemonId) { ...BagFields } }` + BAG_FIELDS,
      { pokemonId }).then((d) => d.obtainPokemon),

  // ---------- Bolsa ----------
  // Una sola petición trae bolsa, equipos y paleta.
  loadCollection: () =>
    gql(`query Collection { bag { ...BagFields } teams { ...TeamFields } teamColors }` + TEAM_FIELDS),

  searchBag: (search) =>
    gql(`query SearchBag($search: String!) { bag(search: $search) { ...BagFields } }` + BAG_FIELDS,
      { search }).then((d) => d.bag),

  release: (id) =>
    gql(`mutation Release($id: Int!) { releaseBagItem(id: $id) }`, { id }),

  createCustom: (input) =>
    gql(`mutation CreateCustom($input: CustomPokemonInput!) { createCustomPokemon(input: $input) { ...BagFields } }` + BAG_FIELDS,
      { input }).then((d) => d.createCustomPokemon),

  updateCustom: (id, input) =>
    gql(`mutation UpdateCustom($id: Int!, $input: CustomPokemonUpdateInput!) {
      updateCustomPokemon(id: $id, input: $input) { ...BagFields }
    }` + BAG_FIELDS, { id, input }).then((d) => d.updateCustomPokemon),

  // ---------- Equipos ----------
  addMember: (teamId, bagItemId) =>
    gql(`mutation AddMember($teamId: Int!, $bagItemId: Int!) { addTeamMember(teamId: $teamId, bagItemId: $bagItemId) { id } }`,
      { teamId, bagItemId }),

  removeMember: (teamId, memberId) =>
    gql(`mutation RemoveMember($teamId: Int!, $memberId: Int!) { removeTeamMember(teamId: $teamId, memberId: $memberId) { id } }`,
      { teamId, memberId }),

  renameTeam: (id, name) =>
    gql(`mutation RenameTeam($id: Int!, $name: String!) { renameTeam(id: $id, name: $name) { id } }`, { id, name }),

  setTeamColor: (id, color) =>
    gql(`mutation SetColor($id: Int!, $color: String!) { setTeamColor(id: $id, color: $color) { id } }`, { id, color }),

  disbandTeam: (id) =>
    gql(`mutation Disband($id: Int!) { disbandTeam(id: $id) { id } }`, { id }),
};