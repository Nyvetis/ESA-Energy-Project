"""Connexion à la base MySQL/MariaDB du vaisseau."""
import mysql.connector

CONFIG = {
    "host": "localhost",
    "user": "workshop",
    "password": "mdp",
    "database": "vaisseau_db",
    "charset": "utf8mb4",
}


def lire(sql, params=(), une_ligne=False):
    """Exécute un SELECT et renvoie les lignes sous forme de dictionnaires."""
    conn = mysql.connector.connect(**CONFIG)
    try:
        curseur = conn.cursor(dictionary=True)
        curseur.execute(sql, params)
        return curseur.fetchone() if une_ligne else curseur.fetchall()
    finally:
        conn.close()


def ecrire(sql, params=()):
    """Exécute un INSERT / UPDATE / DELETE et enregistre la modification."""
    conn = mysql.connector.connect(**CONFIG)
    try:
        curseur = conn.cursor()
        curseur.execute(sql, params)
        conn.commit()
        return curseur.lastrowid
    finally:
        conn.close()
