// Limite le nom saisi à deux mots maximum.
function limitInputToTwoWords() {
    const input = document.getElementById("name");
    const value = input.value;
    const words = value.split(/\s+/); // Sépare la valeur d'entrée par les espaces
    if (words.length > 2) {
      // si il y a plus de deux mots, on ne garde que les deux premiers
      input.value = words.slice(0, 2).join(" ");
    }
  }

const savedNamesKey = "savedNames";
const defaultRoomId = "eqipA";
const roomLabels = {
  vert: "Couloir vert",
  jaune: "Couloir jaune",
  blanc: "Couloir blanc",
  rouge: "Couloir rouge",
  eqipA: "Équipage A",
  eqipB: "Équipage B",
  meds: "Centre médical",
  psych: "Unité psy",
  sas1: "SAS 1",
  serrA: "Serre Hydro A",
  serrB: "Serre Hydro B",
  eau: "Recyclage Eau",
  sas2: "SAS 2",
  genA: "Générateur principal A",
  genB: "Générateur principal B",
  stokA: "Stockage A",
  sasX: "SAS blindé",
  armA: "Poste sécurité & armurerie A",
  servIA: "Serveur IA",
  motrB: "Moteur B",
  armB: "Poste sécurité & armurerie B",
  serv2: "Serveur de secours",
  cmd: "Commandement",
  motrA: "Moteur A",
  stokB: "Stockage B",
  Obsv: "Observatoire",
};
const roomIdByDoorName = Object.fromEntries(
  Object.entries(roomLabels).map(([roomId, name]) => [name, roomId]),
);
let personnel = [];

window.getRoomLabels = () => ({ ...roomLabels });
window.getPersonnelLocations = () => personnel.map(({ id }) => ({ id, roomId: getSavedRoom(id) }));

// Les utilisateurs viennent de l'API ; le stockage local ne garde que leur pièce.
window.setPersonnel = function setPersonnel(users, cards = []) {
  const cardsByUser = new Map();
  cards.forEach((card) => {
    const userCards = cardsByUser.get(card.id_user) || [];
    userCards.push(card);
    cardsByUser.set(card.id_user, userCards);
  });
  personnel = users.map((user) => ({
    id: user.id,
    name: `${user.prenom} ${user.nom}`,
    cards: cardsByUser.get(user.id) || [],
    roomId: getSavedRoom(user.id),
  }));
  renderNames();
  renderRoomAvatars();
};

// Récupère la liste des noms enregistrés dans le stockage du navigateur.
function getRooms() {
  return [...document.querySelectorAll("[data-meta-roomid], [data-meta-RoomId]")].map((room) => ({
    id: room.getAttribute("data-meta-roomid") || room.getAttribute("data-meta-RoomId") || room.getAttribute("data-meta-corridorid"),
    element: room,
  }));
}

function getSavedNames() {
  const savedNames = JSON.parse(localStorage.getItem(savedNamesKey) || "[]");
  return personnel.map((user) => ({ ...user, roomId: getSavedRoom(user.id) }));
}

function getSavedRoom(userId) {
  const savedNames = JSON.parse(localStorage.getItem(savedNamesKey) || "[]");
  const savedUser = savedNames.find((user) => user && user.id === userId);
  return savedUser?.roomId || defaultRoomId;
}

function saveUsers(users) {
  localStorage.setItem(savedNamesKey, JSON.stringify(users.map(({ id, roomId }) => ({ id, roomId }))));
}

function getRoomOptions(selectedRoomId) {
  return getRooms().map(({ id }) => {
    const option = document.createElement("option");
    option.value = id;
    option.textContent = roomLabels[id] || id;
    option.selected = id === selectedRoomId;
    return option;
  });
}

// Reconstruit la liste visible des utilisateurs à partir des noms sauvegardés.
function renderNames() {
  const userList = document.getElementById("userList");
  userList.replaceChildren();

  getSavedNames().forEach((user, index) => {
    const listItem = document.createElement("li");
    const avatar = document.createElement("img");
    avatar.src = generateAvatar(user.name);
    avatar.alt = `Avatar de ${user.name}`;
    avatar.className = "user-avatar";

    const nameLabel = document.createElement("span");
    nameLabel.textContent = user.name;

    const cardLabel = document.createElement("span");
    cardLabel.className = "user-card";
    cardLabel.textContent = user.cards.length
      ? `Cartes : ${user.cards.map((card) => `${card.uid} (niveau ${card.niveau}${card.statut === "active" ? "" : ", désactivée"})`).join(" ; ")}`
      : "Absence de carte d'accès";
    if (user.cards.some((card) => card.statut !== "active")) cardLabel.classList.add("inactive");

    const roomSelect = document.createElement("select");
    roomSelect.className = "user-room";
    roomSelect.setAttribute("aria-label", `Position de ${user.name}`);
    roomSelect.append(...getRoomOptions(user.roomId));
    roomSelect.addEventListener("change", () => {
      const users = getSavedNames().map((user) => ({ id: user.id, roomId: user.roomId }));
      users[index].roomId = roomSelect.value;
      saveUsers(users);
      renderRoomAvatars();
      window.refreshSimulationLocation?.();
    });

    listItem.append(avatar, nameLabel, cardLabel, roomSelect);
    userList.appendChild(listItem);
  });
}

// Valide puis enregistre le nom saisi avant de rafraîchir l'affichage.
function saveName() {
  const input = document.getElementById("name");
  const name = input.value.trim();

  if (!name) {
    return;
  }

  const savedNames = getSavedNames();
  savedNames.push({ name, roomId: defaultRoomId });
  saveUsers(savedNames);
  input.value = "";
  renderNames();
  renderRoomAvatars();
}

function getRoomAvatarTooltip() {
  let tooltip = document.getElementById("roomAvatarTooltip");
  if (!tooltip) {
    tooltip = document.createElement("div");
    tooltip.id = "roomAvatarTooltip";
    tooltip.setAttribute("role", "tooltip");
    document.body.appendChild(tooltip);
  }
  return tooltip;
}

function showRoomAvatarTooltip(event, name) {
  const tooltip = getRoomAvatarTooltip();
  tooltip.textContent = name;
  tooltip.classList.add("is-visible");
  moveRoomAvatarTooltip(event);
}

function moveRoomAvatarTooltip(event) {
  const tooltip = document.getElementById("roomAvatarTooltip");
  if (!tooltip) return;
  tooltip.style.left = `${event.clientX + 12}px`;
  tooltip.style.top = `${event.clientY + 12}px`;
}

function hideRoomAvatarTooltip() {
  document.getElementById("roomAvatarTooltip")?.classList.remove("is-visible");
}

function renderRoomAvatars() {
  document.querySelectorAll(".room-avatar").forEach((avatar) => avatar.remove());
  document.querySelectorAll(".room-avatar-overlay").forEach((overlay) => overlay.remove());
  const svg = document.querySelector("svg");
  if (!svg) return;
  const overlay = document.createElementNS("http://www.w3.org/2000/svg", "g");
  overlay.setAttribute("class", "room-avatar-overlay");
  svg.appendChild(overlay);

  const roomGroups = new Map(getRooms().map((room) => [room.id, room.element]));
  const roomIndexes = new Map();
  getSavedNames().forEach((user) => {
    const room = roomGroups.get(user.roomId) || roomGroups.get(defaultRoomId);
    if (!room) return;

    let bounds = room.querySelector("rect")?.getBBox();
    if (!bounds) return;
    const roomId = room.getAttribute("data-meta-roomid");
    if (roomId === "rouge") {
      const commandRoom = roomGroups.get("cmd");
      const commandBounds = commandRoom?.querySelector("rect")?.getBBox();
      if (commandBounds && commandBounds.x + commandBounds.width < bounds.x + bounds.width) {
        bounds = {
          x: commandBounds.x + commandBounds.width,
          y: bounds.y,
          width: bounds.x + bounds.width - (commandBounds.x + commandBounds.width),
          height: bounds.height,
        };
      }
    }
    const roomIndex = roomIndexes.get(room) || 0;
    roomIndexes.set(room, roomIndex + 1);
    const avatarSize = Math.min(
      22,
      Math.max(12, bounds.height - 4),
      Math.max(12, bounds.width - 4),
    );
    const columns = Math.max(1, Math.floor((bounds.width - 12) / (avatarSize + 3)));
    const column = roomIndex % columns;
    const row = Math.floor(roomIndex / columns);
    const avatar = document.createElementNS("http://www.w3.org/2000/svg", "image");
    avatar.setAttribute("class", "room-avatar");
    const horizontalMargin = Math.min(4, Math.max(2, (bounds.width - avatarSize) / 2));
    avatar.setAttribute("x", bounds.x + horizontalMargin + column * (avatarSize + 3));
    avatar.setAttribute("y", bounds.y + 4 + row * (avatarSize + 3));
    avatar.setAttribute("width", avatarSize);
    avatar.setAttribute("height", avatarSize);
    avatar.setAttribute("href", generateAvatar(user.name));
    avatar.setAttribute("preserveAspectRatio", "xMidYMid slice");
    avatar.addEventListener("mouseenter", (event) => showRoomAvatarTooltip(event, user.name));
    avatar.addEventListener("mousemove", moveRoomAvatarTooltip);
    avatar.addEventListener("mouseleave", hideRoomAvatarTooltip);
    overlay.appendChild(avatar);
  });
}

function moveUserAfterScan(event) {
  if (!event.autorise || !event.id_user) return;
  const roomId = roomIdByDoorName[event.porte];
  if (!roomId || !getRooms().some((room) => room.id === roomId)) return;

  const users = getSavedNames().map((user) => ({
    id: user.id,
    roomId: user.id === event.id_user ? roomId : user.roomId,
  }));
  saveUsers(users);
  renderNames();
  renderRoomAvatars();
  window.refreshSimulationLocation?.();
}

document.addEventListener("DOMContentLoaded", () => {
  renderNames();
  renderRoomAvatars();
});

// Crée une image d'avatar avec une couleur et les initiales du nom.
function generateAvatar(name) {
  const avatarName = (name || document.getElementById("name")?.value || "").trim();
  if (!avatarName) {
    return "";
  }

  const canvas = document.createElement("canvas");
  canvas.width = 96;
  canvas.height = 96;
  const context = canvas.getContext("2d");
  const backgroundColors = ["#f44336", "#E91E63", "#9C27B0", "#3F51B5", "#2196F3", "#009688", "#4CAF50", "#FF9800"];
  // Utilise le nom pour obtenir la même couleur à chaque affichage.
  const colorIndex = [...avatarName].reduce((total, character) => total + character.charCodeAt(0), 0) % backgroundColors.length;
  // Conserve au maximum les deux premières initiales pour rester lisible.
  const initials = avatarName
    .split(/\s+/)
    .map((word) => word.charAt(0))
    .join("")
    .slice(0, 2)
    .toUpperCase();

  context.fillStyle = backgroundColors[colorIndex];
  context.fillRect(0, 0, canvas.width, canvas.height);
  context.font = "bold 42px sans-serif";
  context.fillStyle = "white";
  context.textAlign = "center";
  context.textBaseline = "middle";
  context.fillText(initials, canvas.width / 2, canvas.height / 2);

  return canvas.toDataURL("image/png");
}