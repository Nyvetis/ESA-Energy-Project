"""
API du contrôle d'accès - Workshop Horizon 2080
Lancement :
    uvicorn main:app --host 0.0.0.0 --port 8000

Documentation :
    http://<ip>:8000/docs
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


app = FastAPI(
    title="Yggdrasil - Contrôle d'accès"
)


# ------------------------------------------------------------------
# TEMPS REEL
# ------------------------------------------------------------------

clients: list[WebSocket] = []


async def diffuser(message: dict):
    """
    Envoie un message à toutes les webapps connectées.
    """

    for ws in clients.copy():

        try:
            await ws.send_json(message)

        except Exception:

            if ws in clients:
                clients.remove(ws)


# ------------------------------------------------------------------
# HISTORIQUE
# ------------------------------------------------------------------

# V1 :
# historique conservé en mémoire.
# Les 50 derniers passages sont gardés.

historique: list[dict] = []


# ------------------------------------------------------------------
# DEMANDES DE VALIDATION
# ------------------------------------------------------------------

# Les demandes sont conservées en mémoire.
#
# statut :
#     en_attente
#     valide
#     refuse

demandes: dict[int, dict] = {}

prochain_id = 1


# Délai laissé à l'opérateur pour décider.
# Passé ce temps, l'accès est refusé automatiquement.

DELAI_VALIDATION = 30


def secondes_restantes(demande):
    """
    Nombre de secondes avant le refus automatique.
    """

    return max(
        0,
        round(demande["expire_a"] - time.time())
    )


# ------------------------------------------------------------------
# PORTE DU LECTEUR PHYSIQUE
# ------------------------------------------------------------------

# L'ESP32 envoie porte_id = 0.
#
# L'API utilise alors la porte choisie dans la webapp,
# ce qui permet de tester toutes les portes
# avec un seul lecteur.

porte_lecteur = 1


# ------------------------------------------------------------------
# MOTIFS
# ------------------------------------------------------------------

MOTIF_OPERATEUR = "refuse_operateur"

MOTIF_DELAI = "delai_depasse"


# ------------------------------------------------------------------
# MODELES DE DONNEES
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


class PorteLecteur(BaseModel):
    porte_id: int


class ModifCarte(BaseModel):
    statut: str | None = None
    niveau: int | None = None


# ------------------------------------------------------------------
# SCAN RFID
# ------------------------------------------------------------------

@app.post("/api/scan")
async def scan(data: Scan):

    global prochain_id

    # --------------------------------------------------------------
    # NORMALISATION UID
    # --------------------------------------------------------------

    uid = data.uid.strip().upper()

    # --------------------------------------------------------------
    # VERIFIER LA PORTE
    # --------------------------------------------------------------

    # porte_id = 0 : le lecteur physique.
    # On utilise alors la porte choisie dans la webapp.

    porte_id = data.porte_id or porte_lecteur

    porte = lire(
        "SELECT * FROM porte WHERE id = %s",
        (porte_id,),
        une_ligne=True
    )

    if porte is None:

        raise HTTPException(
            404,
            "Porte inconnue"
        )

    # --------------------------------------------------------------
    # RECHERCHE CARTE
    # --------------------------------------------------------------

    carte = lire(
        """
        SELECT
            c.uid,
            c.niveau,
            c.statut,
            u.nom,
            u.prenom
        FROM carte c
        JOIN `user` u
            ON u.id = c.id_user
        WHERE c.uid = %s
        """,
        (uid,),
        une_ligne=True
    )

    # --------------------------------------------------------------
    # CARTE INCONNUE
    # --------------------------------------------------------------

    if carte is None:

        return await terminer(
            uid,
            porte,
            None,
            False,
            "carte_inconnue"
        )

    # --------------------------------------------------------------
    # CARTE INACTIVE
    # --------------------------------------------------------------

    if carte["statut"] != "active":

        return await terminer(
            uid,
            porte,
            carte,
            False,
            "carte_inactive"
        )

    # --------------------------------------------------------------
    # NIVEAU INSUFFISANT
    # --------------------------------------------------------------

    if carte["niveau"] < porte["niveau_autorisation_requis"]:

        return await terminer(
            uid,
            porte,
            carte,
            False,
            "niveau_insuffisant"
        )

    # ==============================================================
    # PORTE DE NIVEAU 3
    # ==============================================================
    #
    # La carte possède suffisamment de droits.
    #
    # On demande maintenant à un humain de vérifier l'identité.
    #
    # IMPORTANT :
    # sans décision au bout de DELAI_VALIDATION secondes,
    # l'accès est refusé automatiquement.
    #
    # ==============================================================

    if porte["niveau_autorisation_requis"] >= 3:

        demande = {

            "id": prochain_id,

            "heure": datetime.now().strftime(
                "%H:%M:%S"
            ),

            "uid": uid,

            "porte_id": porte["id"],

            "porte": porte["nom"],

            "nom": carte["nom"],

            "prenom": carte["prenom"],

            "niveau": carte["niveau"],

            "statut": "en_attente",

            "expire_a": time.time() + DELAI_VALIDATION,
        }

        # ----------------------------------------------------------
        # ENREGISTRER LA DEMANDE
        # ----------------------------------------------------------

        demandes[prochain_id] = demande

        prochain_id += 1

        # ----------------------------------------------------------
        # INFORMER LA WEBAPP
        # ----------------------------------------------------------

        await diffuser(
            {
                "type": "validation",

                **demande,

                "restant": DELAI_VALIDATION
            }
        )

        # ----------------------------------------------------------
        # LANCER LE COMPTE A REBOURS
        # ----------------------------------------------------------

        asyncio.create_task(
            expirer(demande["id"])
        )

        # ----------------------------------------------------------
        # REPONSE POUR L'UNO
        # ----------------------------------------------------------

        return {

            "en_attente": True,

            "demande_id": demande["id"],

            "nom": carte["nom"],

            "prenom": carte["prenom"],

            "niveau": carte["niveau"],

            "porte": porte["nom"],
        }

    # ==============================================================
    # AUTORISATION DIRECTE
    # ==============================================================

    return await terminer(
        uid,
        porte,
        carte,
        True,
        None
    )


# ------------------------------------------------------------------
# TERMINER UN PASSAGE
# ------------------------------------------------------------------

async def terminer(
    uid,
    porte,
    carte,
    autorise,
    motif
):
    """
    Termine un passage.

    Enregistre le résultat dans l'historique
    puis prévient les webapps connectées.
    """

    evenement = {

        "type": "scan",

        "heure": datetime.now().strftime(
            "%H:%M:%S"
        ),

        "uid": uid,

        "porte_id": porte["id"],

        "porte": porte["nom"],

        "nom": carte["nom"] if carte else None,

        "prenom": carte["prenom"] if carte else None,

        "autorise": autorise,

        "motif": motif,
    }

    # --------------------------------------------------------------
    # HISTORIQUE
    # --------------------------------------------------------------

    historique.insert(
        0,
        evenement
    )

    del historique[50:]

    # --------------------------------------------------------------
    # WEBAPP
    # --------------------------------------------------------------

    await diffuser(
        evenement
    )

    # --------------------------------------------------------------
    # REPONSE
    # --------------------------------------------------------------

    if autorise:

        return {

            "autorise": True,

            "nom": carte["nom"],

            "prenom": carte["prenom"],

            "niveau": carte["niveau"],

            "porte": porte["nom"],
        }

    return {

        "autorise": False,

        "motif": motif
    }


# ------------------------------------------------------------------
# VALIDATION MANUELLE
# ------------------------------------------------------------------

async def cloturer(
    demande,
    valide,
    motif
):
    """
    Termine une demande de validation manuelle.

    valide = True
        -> accès autorisé

    valide = False
        -> accès refusé
    """

    # --------------------------------------------------------------
    # CHANGER LE STATUT
    # --------------------------------------------------------------

    demande["statut"] = (
        "valide"
        if valide
        else "refuse"
    )

    # --------------------------------------------------------------
    # PREPARER LES INFORMATIONS
    # --------------------------------------------------------------

    porte = {

        "id": demande["porte_id"],

        "nom": demande["porte"],
    }

    carte = {

        "nom": demande["nom"],

        "prenom": demande["prenom"],

        "niveau": demande["niveau"],
    }

    # --------------------------------------------------------------
    # INFORMER LA WEBAPP
    # --------------------------------------------------------------

    await diffuser(
        {
            "type": "validation_traitee",

            "id": demande["id"]
        }
    )

    # --------------------------------------------------------------
    # ENREGISTRER LE RESULTAT
    # --------------------------------------------------------------

    await terminer(
        demande["uid"],
        porte,
        carte,
        valide,
        motif
    )


# ------------------------------------------------------------------
# REFUS AUTOMATIQUE
# ------------------------------------------------------------------

async def expirer(
    demande_id
):
    """
    Attend le délai accordé à l'opérateur.

    Si la demande n'a toujours pas été traitée,
    elle est refusée automatiquement.
    """

    await asyncio.sleep(
        DELAI_VALIDATION
    )

    demande = demandes.get(
        demande_id
    )

    if demande is None:
        return

    if demande["statut"] != "en_attente":
        return

    await cloturer(
        demande,
        False,
        MOTIF_DELAI
    )


# ------------------------------------------------------------------
# LISTE DES DEMANDES EN ATTENTE
# ------------------------------------------------------------------

@app.get("/api/demandes")
def demandes_en_attente():
    """
    Renvoie toutes les demandes encore en attente,
    avec le temps restant avant le refus automatique.
    """

    return [

        {
            **demande,

            "restant": secondes_restantes(demande)
        }

        for demande in demandes.values()

        if demande["statut"] == "en_attente"
    ]


# ------------------------------------------------------------------
# STATUT D'UNE DEMANDE
# ------------------------------------------------------------------

@app.get("/api/demandes/{demande_id}")
def etat_demande(
    demande_id: int
):
    """
    Utilisé par l'UNO pour connaître la décision
    de l'opérateur.

    Réponse possible :

        en_attente
        valide
        refuse
    """

    demande = demandes.get(
        demande_id
    )

    if demande is None:

        raise HTTPException(
            404,
            "Demande inconnue"
        )

    return {

        "id": demande_id,

        "statut": demande["statut"]
    }


# ------------------------------------------------------------------
# DECISION OPERATEUR
# ------------------------------------------------------------------

@app.post("/api/demandes/{demande_id}/decision")
async def decider(
    demande_id: int,
    data: Decision
):
    """
    Reçoit la décision de l'opérateur
    depuis la webapp.
    """

    demande = demandes.get(
        demande_id
    )

    if demande is None:

        raise HTTPException(
            404,
            "Demande inconnue"
        )

    # --------------------------------------------------------------
    # VERIFIER SI DEJA TRAITEE
    # --------------------------------------------------------------

    if demande["statut"] != "en_attente":

        raise HTTPException(
            409,
            "Cette demande a déjà été traitée"
        )

    # --------------------------------------------------------------
    # CLOTURER
    # --------------------------------------------------------------

    await cloturer(
        demande,
        data.valide,
        None
        if data.valide
        else MOTIF_OPERATEUR
    )

    return {

        "id": demande_id,

        "statut": demande["statut"]
    }


# ------------------------------------------------------------------
# PORTE REPRESENTEE PAR LE LECTEUR
# ------------------------------------------------------------------

@app.get("/api/lecteur")
def porte_du_lecteur():
    """
    Porte actuellement représentée par le lecteur physique.
    """

    return {
        "porte_id": porte_lecteur
    }


@app.put("/api/lecteur")
async def changer_porte_du_lecteur(
    data: PorteLecteur
):
    """
    Change la porte représentée par le lecteur physique.
    """

    global porte_lecteur

    porte = lire(
        "SELECT * FROM porte WHERE id = %s",
        (data.porte_id,),
        une_ligne=True
    )

    if porte is None:

        raise HTTPException(
            404,
            "Porte inconnue"
        )

    porte_lecteur = data.porte_id

    # Les autres écrans ouverts sont prévenus

    await diffuser(
        {
            "type": "lecteur",

            "porte_id": porte_lecteur
        }
    )

    return {

        "porte_id": porte_lecteur,

        "nom": porte["nom"]
    }


# ------------------------------------------------------------------
# PORTES
# ------------------------------------------------------------------

@app.get("/api/portes")
def liste_portes():

    return lire(
        "SELECT * FROM porte ORDER BY id"
    )


# ------------------------------------------------------------------
# UTILISATEURS
# ------------------------------------------------------------------

@app.get("/api/users")
def liste_users():

    return lire(
        "SELECT * FROM `user` ORDER BY nom"
    )


# ------------------------------------------------------------------
# CARTES
# ------------------------------------------------------------------

@app.get("/api/cartes")
def liste_cartes():

    return lire(
        """
        SELECT
            c.uid,
            c.niveau,
            c.statut,
            c.id_user,
            u.nom,
            u.prenom
        FROM carte c
        JOIN `user` u
            ON u.id = c.id_user
        ORDER BY c.niveau DESC
        """
    )


# ------------------------------------------------------------------
# HISTORIQUE
# ------------------------------------------------------------------

@app.get("/api/historique")
def liste_historique():

    return historique


# ------------------------------------------------------------------
# CREER UTILISATEUR
# ------------------------------------------------------------------

@app.post("/api/users")
def creer_user(
    data: NouvelUtilisateur
):

    nouvel_id = ecrire(
        """
        INSERT INTO `user`
            (nom, prenom)
        VALUES
            (%s, %s)
        """,
        (
            data.nom,
            data.prenom
        )
    )

    return {
        "id": nouvel_id
    }


# ------------------------------------------------------------------
# CREER CARTE
# ------------------------------------------------------------------

@app.post("/api/cartes")
def creer_carte(
    data: NouvelleCarte
):

    if not 1 <= data.niveau <= 3:

        raise HTTPException(
            400,
            "Le niveau doit être entre 1 et 3"
        )

    try:

        ecrire(
            """
            INSERT INTO carte
                (uid, niveau, statut, id_user)
            VALUES
                (%s, %s, 'active', %s)
            """,
            (
                data.uid.strip().upper(),
                data.niveau,
                data.id_user
            )
        )

    except mysql.connector.IntegrityError:

        raise HTTPException(
            409,
            "Cette carte existe déjà ou l'utilisateur est inconnu"
        )

    return {

        "uid": data.uid.strip().upper()
    }


# ------------------------------------------------------------------
# MODIFIER CARTE
# ------------------------------------------------------------------

@app.patch("/api/cartes/{uid}")
def modifier_carte(
    uid: str,
    data: ModifCarte
):

    if data.statut is not None:

        if data.statut not in (
            "active",
            "inactive"
        ):

            raise HTTPException(
                400,
                "Statut invalide"
            )

        ecrire(
            """
            UPDATE carte
            SET statut = %s
            WHERE uid = %s
            """,
            (
                data.statut,
                uid
            )
        )

    if data.niveau is not None:

        if not 1 <= data.niveau <= 3:

            raise HTTPException(
                400,
                "Le niveau doit être entre 1 et 3"
            )

        ecrire(
            """
            UPDATE carte
            SET niveau = %s
            WHERE uid = %s
            """,
            (
                data.niveau,
                uid
            )
        )

    return {

        "uid": uid,

        "statut": data.statut,

        "niveau": data.niveau
    }


# ------------------------------------------------------------------
# WEBSOCKET
# ------------------------------------------------------------------

@app.websocket("/ws")
async def websocket(
    ws: WebSocket
):

    await ws.accept()

    clients.append(ws)

    try:

        while True:

            await ws.receive_text()

    except WebSocketDisconnect:

        if ws in clients:

            clients.remove(ws)


# ------------------------------------------------------------------
# PAGE D'ACCUEIL
# ------------------------------------------------------------------

@app.get("/")
def page_accueil():

    return FileResponse(
        Path(__file__).parent
        / "static"
        / "index.html"
    )
