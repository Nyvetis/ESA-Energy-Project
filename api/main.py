"""
API du contrôle d'accès - Workshop Horizon 2080 (V1)
Lancement : uvicorn main:app --host 0.0.0.0 --port 8000
Documentation automatique : http://<ip>:8000/docs
"""
from datetime import datetime
from pathlib import Path

import mysql.connector
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from db import ecrire, lire

app = FastAPI(title="Yggdrasil - Contrôle d'accès")

# ------------------------------------------------------------------
#  Temps réel : liste des navigateurs connectés à la webapp
# ------------------------------------------------------------------
clients: list[WebSocket] = []


async def diffuser(message: dict):
    """Envoie un message à toutes les webapps ouvertes."""
    for ws in clients.copy():
        try:
            await ws.send_json(message)
        except Exception:
            clients.remove(ws)


# V1 : pas de table de logs, on garde les 50 derniers passages en mémoire
# (ils disparaissent au redémarrage de l'API)
historique: list[dict] = []


# ------------------------------------------------------------------
#  Format des données reçues
# ------------------------------------------------------------------
class Scan(BaseModel):
    uid: str
    porte_id: int
    cible: str | None = None


class NouvelUtilisateur(BaseModel):
    nom: str
    prenom: str


class NouvelleCarte(BaseModel):
    uid: str
    niveau: int
    id_user: int


class StatutCarte(BaseModel):
    statut: str  # "active" ou "inactive"


# ------------------------------------------------------------------
#  Le cœur du système : un badge est passé devant une porte
# ------------------------------------------------------------------
@app.post("/api/scan")
async def scan(data: Scan):
    uid = data.uid.strip().upper()
    lieu = data.cible.strip() if data.cible else None

    porte = lire("SELECT * FROM porte WHERE id = %s", (data.porte_id,), une_ligne=True)
    if porte is None:
        raise HTTPException(404, "Porte inconnue")

    carte = lire(
        """SELECT c.uid, c.niveau, c.statut, c.id_user, u.nom, u.prenom
           FROM carte c JOIN `user` u ON u.id = c.id_user
           WHERE c.uid = %s""",
        (uid,),
        une_ligne=True,
    )

    # Une salle de niveau 0 reste accessible sans carte.
    if porte["niveau_autorisation_requis"] == 0:
        reponse = {
            "autorise": True,
            "nom": carte["nom"] if carte else None,
            "prenom": carte["prenom"] if carte else None,
            "niveau": carte["niveau"] if carte else 0,
            "porte": lieu or porte["nom"],
        }
    # Les vérifications des zones sécurisées, dans l'ordre.
    elif carte is None:
        reponse = {"autorise": False, "motif": "carte_inconnue"}
    elif carte["statut"] != "active":
        reponse = {"autorise": False, "motif": "carte_inactive"}
    elif carte["niveau"] < porte["niveau_autorisation_requis"]:
        reponse = {"autorise": False, "motif": "niveau_insuffisant"}
    else:
        reponse = {
            "autorise": True,
            "nom": carte["nom"],
            "prenom": carte["prenom"],
            "niveau": carte["niveau"],
            "porte": lieu or porte["nom"],
        }

    # On prévient la webapp en temps réel
    evenement = {
        "heure": datetime.now().strftime("%H:%M:%S"),
        "uid": uid,
        "porte_id": porte["id"],
        "porte": lieu or porte["nom"],
        "id_user": carte["id_user"] if carte else None,
        "nom": carte["nom"] if carte else None,
        "prenom": carte["prenom"] if carte else None,
        "autorise": reponse["autorise"],
        "motif": reponse.get("motif"),
    }
    historique.insert(0, evenement)
    del historique[50:]
    await diffuser(evenement)

    return reponse


# ------------------------------------------------------------------
#  Lecture des données pour la webapp
# ------------------------------------------------------------------
@app.get("/api/portes")
def liste_portes():
    return lire("SELECT * FROM porte ORDER BY id")


@app.get("/api/users")
def liste_users():
    return lire("SELECT * FROM `user` ORDER BY nom")


@app.get("/api/cartes")
def liste_cartes():
    return lire(
        """SELECT c.uid, c.niveau, c.statut, c.id_user, u.nom, u.prenom
           FROM carte c JOIN `user` u ON u.id = c.id_user
           ORDER BY c.niveau DESC"""
    )


@app.get("/api/historique")
def liste_historique():
    return historique


# ------------------------------------------------------------------
#  Gestion des users et des cartes
# ------------------------------------------------------------------
@app.post("/api/users")
def creer_user(data: NouvelUtilisateur):
    nouvel_id = ecrire(
        "INSERT INTO `user` (nom, prenom) VALUES (%s, %s)", (data.nom, data.prenom)
    )
    return {"id": nouvel_id}


@app.post("/api/cartes")
def creer_carte(data: NouvelleCarte):
    uid = data.uid.strip().upper()
    if not uid or any(caractere not in "0123456789ABCDEF" for caractere in uid):
        raise HTTPException(400, "L'UID doit contenir uniquement des caractères hexadécimaux")
    if not 0 <= data.niveau <= 3:
        raise HTTPException(400, "Le niveau doit être entre 0 et 3")
    try:
        ecrire(
            "INSERT INTO carte (uid, niveau, statut, id_user) VALUES (%s, %s, 'active', %s)",
            (uid, data.niveau, data.id_user),
        )
    except mysql.connector.IntegrityError:
        raise HTTPException(409, "Cette carte existe déjà ou l'utilisateur est inconnu")
    return {"uid": uid}


@app.patch("/api/cartes/{uid}")
def changer_statut(uid: str, data: StatutCarte):
    if data.statut not in ("active", "inactive"):
        raise HTTPException(400, "Statut invalide")
    uid = uid.strip().upper()
    ecrire("UPDATE carte SET statut = %s WHERE uid = %s", (data.statut, uid))
    return {"uid": uid, "statut": data.statut}


# ------------------------------------------------------------------
#  WebSocket + page de la webapp
# ------------------------------------------------------------------
@app.websocket("/ws")
async def websocket(ws: WebSocket):
    await ws.accept()
    clients.append(ws)
    try:
        while True:
            await ws.receive_text()  # on garde la connexion ouverte
    except WebSocketDisconnect:
        clients.remove(ws)


@app.get("/")
def page_accueil():
    return FileResponse(Path(__file__).parent / "static" / "index.html")


app.mount("/", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
