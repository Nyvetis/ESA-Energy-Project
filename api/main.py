"""
API du contrôle d'accès - Workshop Horizon 2080 (V1)
Lancement : uvicorn main:app --host 0.0.0.0 --port 8000
Documentation automatique : http://<ip>:8000/docs
"""
import asyncio
import time
from datetime import datetime
from pathlib import Path

import mysql.connector
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
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

# Demandes de validation manuelle (portes de niveau 3), gardées en mémoire
# statut : "en_attente", "valide" ou "refuse"
demandes: dict[int, dict] = {}
prochain_id = 1

MOTIF_OPERATEUR = "refuse_operateur"
MOTIF_DELAI = "delai_depasse"
DELAI_VALIDATION = 30  # secondes avant un refus automatique


def secondes_restantes(demande):
    return max(0, round(demande["expire_a"] - time.time()))


# ------------------------------------------------------------------
#  Format des données reçues
# ------------------------------------------------------------------
class Scan(BaseModel):
    uid: str
    porte_id: int


class NouvelUtilisateur(BaseModel):
    nom: str
    prenom: str


class NouvelleCarte(BaseModel):
    uid: str
    niveau: int
    id_user: int


class Decision(BaseModel):
    valide: bool


class ModifCarte(BaseModel):
    # Les deux champs sont optionnels : on envoie seulement ce qu'on veut changer
    statut: str | None = None   # "active" ou "inactive"
    niveau: int | None = None   # 1 à 3


# ------------------------------------------------------------------
#  Le cœur du système : un badge est passé devant une porte
# ------------------------------------------------------------------
@app.post("/api/scan")
async def scan(data: Scan):
    global prochain_id
    uid = data.uid.strip().upper()

    porte = lire("SELECT * FROM porte WHERE id = %s", (data.porte_id,), une_ligne=True)
    if porte is None:
        raise HTTPException(404, "Porte inconnue")

    carte = lire(
        """SELECT c.uid, c.niveau, c.statut, u.nom, u.prenom
           FROM carte c JOIN `user` u ON u.id = c.id_user
           WHERE c.uid = %s""",
        (uid,),
        une_ligne=True,
    )

    # Les 3 vérifications, dans l'ordre
    if carte is None:
        return await terminer(uid, porte, None, False, "carte_inconnue")
    if carte["statut"] != "active":
        return await terminer(uid, porte, carte, False, "carte_inactive")
    if carte["niveau"] < porte["niveau_autorisation_requis"]:
        return await terminer(uid, porte, carte, False, "niveau_insuffisant")

    # Porte de niveau 3 : un opérateur doit confirmer l'identité à la caméra
    if porte["niveau_autorisation_requis"] >= 3:
        demande = {
            "id": prochain_id,
            "heure": datetime.now().strftime("%H:%M:%S"),
            "uid": uid,
            "porte_id": porte["id"],
            "porte": porte["nom"],
            "nom": carte["nom"],
            "prenom": carte["prenom"],
            "niveau": carte["niveau"],
            "statut": "en_attente",
            "expire_a": time.time() + DELAI_VALIDATION,
        }
        demandes[prochain_id] = demande
        prochain_id += 1
        await diffuser({"type": "validation", **demande, "restant": DELAI_VALIDATION})
        # Refus automatique si personne ne décide à temps
        asyncio.create_task(expirer(demande["id"]))
        return {"en_attente": True, "demande_id": demande["id"],
                "nom": carte["nom"], "prenom": carte["prenom"]}

    return await terminer(uid, porte, carte, True, None)


async def terminer(uid, porte, carte, autorise, motif):
    """Enregistre le passage, prévient la webapp et prépare la réponse pour l'ESP32."""
    evenement = {
        "type": "scan",
        "heure": datetime.now().strftime("%H:%M:%S"),
        "uid": uid,
        "porte_id": porte["id"],
        "porte": porte["nom"],
        "nom": carte["nom"] if carte else None,
        "prenom": carte["prenom"] if carte else None,
        "autorise": autorise,
        "motif": motif,
    }
    historique.insert(0, evenement)
    del historique[50:]
    await diffuser(evenement)

    if autorise:
        return {"autorise": True, "nom": carte["nom"], "prenom": carte["prenom"],
                "niveau": carte["niveau"], "porte": porte["nom"]}
    return {"autorise": False, "motif": motif}


# ------------------------------------------------------------------
#  Validation manuelle par un opérateur
# ------------------------------------------------------------------
async def cloturer(demande, valide, motif):
    """Termine une demande : met à jour son statut et prévient tout le monde."""
    demande["statut"] = "valide" if valide else "refuse"
    porte = {"id": demande["porte_id"], "nom": demande["porte"]}
    carte = {"nom": demande["nom"], "prenom": demande["prenom"], "niveau": demande["niveau"]}
    await diffuser({"type": "validation_traitee", "id": demande["id"]})
    await terminer(demande["uid"], porte, carte, valide, motif)


async def expirer(demande_id):
    """Attend le délai, puis refuse la demande si elle n'a pas été traitée."""
    await asyncio.sleep(DELAI_VALIDATION)
    demande = demandes.get(demande_id)
    if demande and demande["statut"] == "en_attente":
        await cloturer(demande, False, MOTIF_DELAI)


@app.get("/api/demandes")
def demandes_en_attente():
    """Liste des demandes pas encore traitées (utile au rechargement de la page)."""
    return [{**d, "restant": secondes_restantes(d)}
            for d in demandes.values() if d["statut"] == "en_attente"]


@app.get("/api/demandes/{demande_id}")
def etat_demande(demande_id: int):
    """Appelée en boucle par l'ESP32 pour savoir si l'opérateur a décidé."""
    demande = demandes.get(demande_id)
    if demande is None:
        raise HTTPException(404, "Demande inconnue")
    return {"id": demande_id, "statut": demande["statut"]}


@app.post("/api/demandes/{demande_id}/decision")
async def decider(demande_id: int, data: Decision):
    demande = demandes.get(demande_id)
    if demande is None:
        raise HTTPException(404, "Demande inconnue")
    if demande["statut"] != "en_attente":
        raise HTTPException(409, "Cette demande a déjà été traitée")

    await cloturer(demande, data.valide, None if data.valide else MOTIF_OPERATEUR)
    return {"id": demande_id, "statut": demande["statut"]}


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
    if not 1 <= data.niveau <= 3:
        raise HTTPException(400, "Le niveau doit être entre 1 et 3")
    try:
        ecrire(
            "INSERT INTO carte (uid, niveau, statut, id_user) VALUES (%s, %s, 'active', %s)",
            (data.uid.strip().upper(), data.niveau, data.id_user),
        )
    except mysql.connector.IntegrityError:
        raise HTTPException(409, "Cette carte existe déjà ou l'utilisateur est inconnu")
    return {"uid": data.uid.strip().upper()}


@app.patch("/api/cartes/{uid}")
def modifier_carte(uid: str, data: ModifCarte):
    if data.statut is not None:
        if data.statut not in ("active", "inactive"):
            raise HTTPException(400, "Statut invalide")
        ecrire("UPDATE carte SET statut = %s WHERE uid = %s", (data.statut, uid))

    if data.niveau is not None:
        if not 1 <= data.niveau <= 3:
            raise HTTPException(400, "Le niveau doit être entre 1 et 3")
        ecrire("UPDATE carte SET niveau = %s WHERE uid = %s", (data.niveau, uid))

    return {"uid": uid, "statut": data.statut, "niveau": data.niveau}


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
