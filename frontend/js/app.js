import { api } from "./api.js";

const PAGE_SIZE = 24;
const TEAM_SIZE = 6;
const TYPES = {
  normal: "Normal", fire: "Fuego", water: "Agua", electric: "Eléctrico", grass: "Planta", ice: "Hielo",
  fighting: "Lucha", poison: "Veneno", ground: "Tierra", flying: "Volador", psychic: "Psíquico", bug: "Bicho",
  rock: "Roca", ghost: "Fantasma", dragon: "Dragón", dark: "Siniestro", steel: "Acero", fairy: "Hada",
};
const COLOR_NAMES = {
  red: "Rojo", black: "Negro", white: "Blanco", blue: "Azul",
  green: "Verde", yellow: "Amarillo", purple: "Morado", orange: "Naranja",
};
const STATS = [
  ["hp", "PS"], ["attack", "Ataque"], ["defense", "Defensa"],
  ["specialAttack", "At. especial"], ["specialDefense", "Def. especial"], ["speed", "Velocidad"],
];

const state = {
  market: [], marketTerm: "", marketHasMore: false,
  bag: [], bagView: [], bagTerm: "",
  teams: [], colors: [], openTeamId: null,
};

const $ = (selector, root = document) => root.querySelector(selector);
const clone = (id) => $(`#${id}`).content.firstElementChild.cloneNode(true);
const display = (name) => name.charAt(0).toUpperCase() + name.slice(1);
// Los oficiales llegan en minúsculas ("mr-mime"); los personalizados se muestran tal cual los escribió el usuario.
const nameOf = (p) => (p.source === "CUSTOM" ? p.name : display(p.name));

// ---------- Utilidades de interfaz ----------

function setStatus(el, text, kind = "") {
  el.textContent = text;
  el.className = `status${kind ? ` is-${kind}` : ""}`;
}

let toastTimer;
function toast(text, isError = false) {
  const el = $("#toast");
  el.textContent = text;
  el.classList.toggle("is-error", isError);
  el.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (el.hidden = true), 3500);
}

function confirmDialog(message, okLabel) {
  const dialog = $("#confirm-dialog");
  $("#confirm-message").textContent = message;
  $("#confirm-ok").textContent = okLabel;
  dialog.returnValue = "";
  dialog.showModal();
  return new Promise((resolve) =>
    dialog.addEventListener("close", () => resolve(dialog.returnValue === "ok"), { once: true }));
}

function fillSprite(el, pokemon) {
  el.replaceChildren();
  if (pokemon.sprite) {
    const img = new Image();
    img.src = pokemon.sprite;
    img.alt = "";
    img.loading = "lazy";
    img.onerror = () => fillSprite(el, { ...pokemon, sprite: null }); // sin imagen: se usa la inicial
    el.append(img);
  } else {
    const letter = document.createElement("span");
    letter.className = `sprite-letter type-${pokemon.types[0]}`;
    letter.textContent = pokemon.name.charAt(0);
    el.append(letter);
  }
}

function fillTypes(el, types) {
  el.replaceChildren(...types.map((type) => {
    const chip = document.createElement("span");
    chip.className = `chip type-${type}`;
    chip.textContent = TYPES[type] ?? type;
    return chip;
  }));
}

// ---------- Navegación ----------

function showView(view) {
  document.querySelectorAll(".view").forEach((s) => (s.hidden = s.id !== `view-${view}`));
  document.querySelectorAll(".tab").forEach((t) => {
    if (t.dataset.view === view) t.setAttribute("aria-current", "page");
    else t.removeAttribute("aria-current");
  });
}

// ---------- Mercado (Explorar) ----------

async function loadMarket(reset) {
  const status = $("#explore-status");
  if (reset) {
    state.market = [];
    $("#results").replaceChildren();
  }
  $("#load-more").hidden = true;
  setStatus(status, "Cargando Pokémon…", "loading");
  try {
    const page = await api.searchPokemon(state.marketTerm, PAGE_SIZE, state.market.length);
    state.market.push(...page);
    state.marketHasMore = page.length === PAGE_SIZE;
    renderMarket();
    if (state.market.length === 0) {
      setStatus(status, state.marketTerm ? `No hay Pokémon con “${state.marketTerm}”.` : "El catálogo está vacío.");
    } else {
      setStatus(status, "");
    }
  } catch (err) {
    setStatus(status, err.message, "error");
  }
}

function renderMarket() {
  $("#results").replaceChildren(...state.market.map((p) => {
    const li = clone("tpl-market-card");
    fillSprite($(".sprite", li), p);
    $(".dex-id", li).textContent = `#${String(p.id).padStart(4, "0")}`;
    $(".card-name", li).textContent = display(p.name);
    fillTypes($(".types", li), p.types);
    $(".tag-owned", li).hidden = p.bagItemId === null;
    $(".card", li).addEventListener("click", () => openMarketDetail(p.name));
    return li;
  }));
  $("#load-more").hidden = !state.marketHasMore;
}

function setMarketOwnership(pokemonId, bagItemId) {
  const item = state.market.find((p) => p.id === pokemonId);
  if (item) item.bagItemId = bagItemId;
  renderMarket();
}

// ---------- Detalle (compartido por mercado y bolsa) ----------

function fillDetail(p, idLabel) {
  fillSprite($("#detail-sprite"), p);
  $("#detail-id").textContent = idLabel;
  $("#detail-name").textContent = nameOf(p);
  fillTypes($("#detail-types"), p.types);
  $("#detail-height").textContent = p.height != null ? `${p.height} m` : "—";
  $("#detail-weight").textContent = p.weight != null ? `${p.weight} kg` : "—";
  $("#detail-abilities-row").hidden = p.abilities.length === 0;
  $("#detail-abilities").textContent = p.abilities.join(", ");
  $("#detail-stats").replaceChildren(...STATS.map(([key, label]) => {
    const li = clone("tpl-stat");
    $(".stat-name", li).textContent = label;
    $(".stat-value", li).textContent = p.stats[key];
    $(".stat-bar span", li).style.setProperty("--value", p.stats[key]);
    return li;
  }));
}

function button(label, className, onClick, disabled = false) {
  const b = document.createElement("button");
  b.type = "button";
  b.className = `btn ${className}`;
  b.textContent = label;
  b.disabled = disabled;
  b.addEventListener("click", onClick);
  return b;
}

async function openMarketDetail(name) {
  const dialog = $("#detail-dialog");
  const status = $("#explore-status");
  setStatus(status, "Cargando detalle…", "loading");
  try {
    const p = await api.pokemonDetail(name);
    setStatus(status, "");
    if (!p) return toast("Ese Pokémon no existe.", true);
    fillDetail(p, `#${String(p.id).padStart(4, "0")}`);
    renderMarketActions(p);
    if (!dialog.open) dialog.showModal();
  } catch (err) {
    setStatus(status, "");
    toast(err.message, true);
  }
}

function renderMarketActions(p) {
  const actions = $("#detail-actions");
  if (p.bagItemId !== null) {
    actions.replaceChildren(button("Ya está en tu bolsa", "btn-ghost", () => {}, true));
    return;
  }
  actions.replaceChildren(button("Obtener", "btn-primary", async (e) => {
    e.target.disabled = true;
    try {
      const item = await api.obtain(p.id);
      p.bagItemId = item.id;
      toast(`${nameOf(item)} está en tu bolsa.`);
      renderMarketActions(p);
      setMarketOwnership(p.id, item.id);
      await refreshCollection();
    } catch (err) {
      e.target.disabled = false;
      toast(err.message, true);
    }
  }));
}

function openBagDetail(bagItemId) {
  const item = state.bag.find((i) => i.id === bagItemId);
  if (!item) return;
  fillDetail(item, item.source === "CUSTOM" ? "Personalizado" : `#${String(item.pokemonId).padStart(4, "0")}`);
  renderBagActions(item);
  const dialog = $("#detail-dialog");
  if (!dialog.open) dialog.showModal();
}

function renderBagActions(item) {
  const title = document.createElement("h3");
  title.textContent = "Agregar a un equipo";
  const teamButtons = document.createElement("div");
  teamButtons.className = "action-row";
  teamButtons.append(...state.teams.map((team) => {
    const inTeam = team.members.some((m) => m.pokemon.id === item.id);
    const full = team.size >= TEAM_SIZE;
    const label = inTeam ? `${team.name} ✓` : `${team.name} (${team.size}/${TEAM_SIZE})`;
    return button(label, "btn-ghost btn-small", async () => {
      try {
        await api.addMember(team.id, item.id);
        toast(`${nameOf(item)} se agregó a ${team.name}.`);
        await refreshCollection();
        openBagDetail(item.id);
      } catch (err) {
        toast(err.message, true);
      }
    }, inTeam || full);
  }));

  const manage = document.createElement("div");
  manage.className = "action-row";
  if (item.source === "CUSTOM") {
    manage.append(button("Editar", "btn-ghost btn-small", () => openEdit(item)));
  }
  const isCustom = item.source === "CUSTOM";
  manage.append(button(isCustom ? "Borrar" : "Soltar", "btn-ghost btn-small", () => releaseItem(item)));

  $("#detail-actions").replaceChildren(title, teamButtons, manage);
}

async function releaseItem(item) {
  const isCustom = item.source === "CUSTOM";
  const inTeams = item.teamCount > 0
    ? ` Está en ${item.teamCount} ${item.teamCount === 1 ? "equipo" : "equipos"} y saldrá de ${item.teamCount === 1 ? "él" : "ellos"}.`
    : "";
  const message = isCustom
    ? `¿Seguro que quieres borrar a ${nameOf(item)}?${inTeams} Lo perderás para siempre.`
    : `¿Seguro que quieres soltar a ${nameOf(item)}?${inTeams} Volverá al mercado.`;
  $("#detail-dialog").close();
  if (!(await confirmDialog(message, isCustom ? "Borrar" : "Soltar"))) return;
  try {
    await api.release(item.id);
    toast(isCustom ? `${nameOf(item)} fue borrado.` : `${nameOf(item)} volvió al mercado.`);
    if (!isCustom) setMarketOwnership(item.pokemonId, null);
    await refreshCollection();
  } catch (err) {
    toast(err.message, true);
  }
}

// ---------- Bolsa (Mis Pokémon) ----------

async function refreshCollection() {
  try {
    const data = await api.loadCollection();
    state.bag = data.bag;
    state.teams = data.teams;
    state.colors = data.teamColors;
    state.bagView = state.bagTerm ? await api.searchBag(state.bagTerm) : state.bag;
    renderBag();
    renderTeams();
  } catch (err) {
    setStatus($("#bag-status"), err.message, "error");
    setStatus($("#teams-status"), err.message, "error");
  }
}

function renderBag() {
  const status = $("#bag-status");
  if (state.bagView.length === 0) {
    setStatus(status, state.bagTerm
      ? `No tienes Pokémon con “${state.bagTerm}”.`
      : "Tu bolsa está vacía. Obtén Pokémon en Explorar o crea uno aquí.");
  } else {
    setStatus(status, "");
  }
  $("#bag-list").replaceChildren(...state.bagView.map((item) => {
    const li = clone("tpl-bag-card");
    fillSprite($(".sprite", li), item);
    $(".card-name", li).textContent = nameOf(item);
    fillTypes($(".types", li), item.types);
    $(".hp", li).textContent = `PS ${item.stats.hp}`;
    $(".tag-custom", li).hidden = item.source !== "CUSTOM";
    $(".card", li).addEventListener("click", () => openBagDetail(item.id));
    return li;
  }));
}

function readCustomForm(form) {
  const f = new FormData(form);
  const number = (key) => Number(f.get(key));
  return {
    name: f.get("name").trim() || null,
    type1: f.get("type1"),
    type2: f.get("type2") || null,
    hp: number("hp"), attack: number("attack"), defense: number("defense"),
    specialAttack: number("specialAttack"), specialDefense: number("specialDefense"), speed: number("speed"),
    height: number("height"), weight: number("weight"),
  };
}

async function onCreateCustom(event) {
  event.preventDefault();
  const form = event.target;
  const error = $(".form-error", form);
  error.textContent = "";
  if (!form.checkValidity()) {
    form.reportValidity();
    return;
  }
  const submit = $("button[type=submit]", form);
  submit.disabled = true;
  try {
    const item = await api.createCustom(readCustomForm(form));
    form.reset();
    toast(`${item.name} se creó y ya está en tu bolsa.`);
    await refreshCollection();
  } catch (err) {
    error.textContent = err.message;
  } finally {
    submit.disabled = false;
  }
}

function openEdit(item) {
  $("#detail-dialog").close();
  const form = $("#edit-form");
  form.dataset.id = item.id;
  form.name.value = item.name;
  form.height.value = item.height;
  form.weight.value = item.weight;
  $(".form-error", form).textContent = "";
  $("#edit-dialog").showModal();
}

async function onEditCustom(event) {
  event.preventDefault();
  const form = event.target;
  if (!form.checkValidity()) return form.reportValidity();
  try {
    const item = await api.updateCustom(Number(form.dataset.id), {
      name: form.name.value.trim(), height: Number(form.height.value), weight: Number(form.weight.value),
    });
    $("#edit-dialog").close();
    toast(`${item.name} se actualizó.`);
    await refreshCollection();
  } catch (err) {
    $(".form-error", form).textContent = err.message;
  }
}

// ---------- Equipos ----------

function renderTeams() {
  setStatus($("#teams-status"), "");
  $("#teams-list").replaceChildren(...state.teams.map(renderTeam));
}

function renderTeam(team) {
  const card = clone("tpl-team");
  card.classList.add(`team-color-${team.color}`);
  card.classList.toggle("is-inactive", team.size === 0);
  card.open = team.id === state.openTeamId;
  card.addEventListener("toggle", () => {
    if (card.open) state.openTeamId = team.id;
    else if (state.openTeamId === team.id) state.openTeamId = null;
  });

  $(".team-name", card).textContent = team.name;
  $(".team-count", card).textContent = `${team.size}/${TEAM_SIZE}`;

  // Vista cerrada: imagen del primero agregado + nombre, tipo y vida de cada uno
  if (team.members.length) fillSprite($(".team-cover", card), team.members[0].pokemon);
  $(".team-rows", card).replaceChildren(...team.members.map(({ pokemon }) => {
    const row = clone("tpl-team-row");
    $(".row-name", row).textContent = nameOf(pokemon);
    $(".row-name", row).title = nameOf(pokemon);
    fillTypes($(".types", row), pokemon.types.slice(0, 1)); // cerrada: solo el tipo principal
    $(".row-hp", row).textContent = `PS ${pokemon.stats.hp}`;
    return row;
  }));

  // Vista abierta: todos sus datos
  $(".members", card).replaceChildren(...team.members.map(({ memberId, pokemon }) => {
    const li = clone("tpl-member");
    fillSprite($(".member-sprite", li), pokemon);
    $(".member-name", li).textContent = nameOf(pokemon);
    fillTypes($(".types", li), pokemon.types);
    $(".member-stats", li).replaceChildren(...STATS.map(([key, label]) => {
      const pair = document.createElement("div");
      const dt = document.createElement("dt");
      const dd = document.createElement("dd");
      dt.textContent = label;
      dd.textContent = pokemon.stats[key];
      pair.append(dt, dd);
      return pair;
    }));
    const remove = $("[data-action=remove]", li);
    remove.setAttribute("aria-label", `Quitar a ${nameOf(pokemon)} de ${team.name}`);
    remove.addEventListener("click", () => teamAction(() => api.removeMember(team.id, memberId),
      `${nameOf(pokemon)} salió de ${team.name}.`));
    return li;
  }));

  $(".swatches", card).replaceChildren(...state.colors.map((color) => {
    const swatch = document.createElement("button");
    swatch.type = "button";
    swatch.className = `swatch team-color-${color}`;
    swatch.setAttribute("aria-label", COLOR_NAMES[color] ?? color);
    swatch.setAttribute("aria-pressed", String(color === team.color));
    swatch.addEventListener("click", () => teamAction(() => api.setTeamColor(team.id, color)));
    return swatch;
  }));

  $("[data-action=rename]", card).addEventListener("click", () => openRename(team));
  $("[data-action=disband]", card).addEventListener("click", async () => {
    if (await confirmDialog(`¿Seguro que quieres desintegrar el ${team.name}?`, "Desintegrar")) {
      teamAction(() => api.disbandTeam(team.id), `${team.name} fue desintegrado.`);
    }
  });
  return card;
}

async function teamAction(request, successMessage) {
  try {
    await request();
    if (successMessage) toast(successMessage);
    await refreshCollection();
  } catch (err) {
    toast(err.message, true);
  }
}

function openRename(team) {
  const form = $("#rename-form");
  form.dataset.id = team.id;
  form.name.value = team.name;
  $(".form-error", form).textContent = "";
  $("#rename-dialog").showModal();
}

async function onRename(event) {
  event.preventDefault();
  const form = event.target;
  if (!form.checkValidity()) return form.reportValidity();
  try {
    await api.renameTeam(Number(form.dataset.id), form.name.value.trim());
    $("#rename-dialog").close();
    await refreshCollection();
  } catch (err) {
    $(".form-error", form).textContent = err.message;
  }
}

// ---------- Arranque ----------

function fillTypeSelects() {
  document.querySelectorAll(".type-select").forEach((select) => {
    if (select.dataset.optional !== undefined) select.add(new Option("Ninguno", ""));
    Object.entries(TYPES).forEach(([value, label]) => select.add(new Option(label, value)));
  });
}

function bindEvents() {
  document.querySelectorAll(".tab").forEach((tab) => tab.addEventListener("click", () => showView(tab.dataset.view)));

  $("#search-form").addEventListener("submit", (e) => {
    e.preventDefault();
    state.marketTerm = $("#search-input").value.trim();
    loadMarket(true);
  });
  $("#load-more").addEventListener("click", () => loadMarket(false));

  $("#bag-search-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    state.bagTerm = $("#bag-search-input").value.trim();
    setStatus($("#bag-status"), "Buscando…", "loading");
    try {
      state.bagView = state.bagTerm ? await api.searchBag(state.bagTerm) : state.bag;
      renderBag();
    } catch (err) {
      setStatus($("#bag-status"), err.message, "error");
    }
  });

  $("#custom-form").addEventListener("submit", onCreateCustom);
  $("#edit-form").addEventListener("submit", onEditCustom);
  $("#rename-form").addEventListener("submit", onRename);

  document.querySelectorAll("[data-close]").forEach((b) => b.addEventListener("click", () => b.closest("dialog").close()));
  document.querySelectorAll("dialog").forEach((dialog) =>
    dialog.addEventListener("click", (e) => {
      if (e.target !== dialog) return;
      const r = dialog.getBoundingClientRect();
      const outside = e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom;
      if (outside) dialog.close(); // clic en el fondo oscuro = cerrar
    }));
}

fillTypeSelects();
bindEvents();
setStatus($("#bag-status"), "Cargando tu bolsa…", "loading");
setStatus($("#teams-status"), "Cargando equipos…", "loading");
loadMarket(true);
refreshCollection();