# Yggdrasil — Contrôle d'accès du vaisseau

Projet réalisé pour le **Workshop EPSI B3 « Horizon 2080 »** (septembre 2026), pilier *DeepTech & Secure Systems*.

À bord d'un vaisseau interstellaire coupé de la Terre, chaque zone doit être protégée. Chaque membre d'équipage possède une carte d'accès RFID : en la passant devant le lecteur d'une porte, le système vérifie son niveau d'autorisation et ouvre ou refuse l'accès. Tout est géré par un **serveur de bord autonome** (Raspberry Pi), sans dépendre d'Internet.

---

## Sommaire
1. [Fonctionnement](#fonctionnement)
2. [Architecture](#architecture)
3. [Matériel et câblage](#matériel-et-câblage)
4. [Base de données](#base-de-données)
5. [API](#api)
6. [Installation sur le Raspberry Pi](#installation-sur-le-raspberry-pi)
7. [Configuration de l'ESP32](#configuration-de-lesp32)
8. [Scénario de démonstration](#scénario-de-démonstration)
9. [Limites de la V1 et pistes V2](#limites-de-la-v1-et-pistes-v2)

---

## Fonctionnement

1. Un astronaute passe sa carte devant le lecteur RC522.
2. L'ESP32 lit l'**UID** de la carte et l'envoie à l'API avec le numéro de la porte.
3. L'API vérifie, dans l'ordre :
   - que la carte existe (`carte_inconnue` sinon),
   - qu'elle est active (`carte_inactive` sinon),
   - que son niveau est suffisant : `carte.niveau >= porte.niveau_autorisation_requis` (`niveau_insuffisant` sinon).
4. L'ESP32 affiche le résultat : **LED verte + 1 bip** si autorisé, **LED rouge + 3 bips** si refusé.
5. L'interface web se met à jour en temps réel : la porte passe au vert ou au rouge et le passage apparaît dans l'historique.

Si le serveur est injoignable, la porte **reste fermée** (principe *fail-secure*) et la LED rouge clignote.

---

## Architecture

```
[Carte RFID] → [ESP32-S3-CAM + RC522] ──POST /api/scan──→ [API FastAPI] ←→ [MariaDB]
                                                                 │
                                                             WebSocket
                                                                 ↓
                                                        [Interface web]
```

L'API et la base tournent sur le **Raspberry Pi** (`ESA-cyber`). L'ESP32, le Raspberry et les navigateurs doivent être sur le **même réseau Wi-Fi**.

| Partie | Technologie |
|---|---|
| Lecteur de porte | ESP32-S3-CAM + RC522, Arduino C++ |
| API | Python, FastAPI |
| Base de données | MariaDB (compatible MySQL) |
| Interface | HTML / CSS / JavaScript, servie par l'API |
| Temps réel | WebSocket |
| Serveur | Raspberry Pi 5, Raspberry Pi OS 64-bit |

### Arborescence
```
horizon2080/
├── api/
│   ├── main.py            # routes de l'API
│   ├── db.py              # connexion à la base
│   ├── requirements.txt   # dépendances Python
│   └── static/index.html  # interface web
├── bdd/
│   ├── bdd_vaisseau.sql   # création de la base et des tables
│   └── donnees_test.sql   # données de démo (users, portes)
├── esp32/
│   └── lecteur_porte.ino  # programme du lecteur de porte
├── CLAUDE.md              # contexte du projet pour l'assistant IA
└── README.md
```

---

## Matériel et câblage

- 1 ESP32-S3-CAM
- 1 lecteur RFID RC522 (**3,3 V uniquement**, jamais 5 V)
- 1 badge porte-clé + 1 carte « premium »
- 1 LED verte, 1 LED rouge (avec résistances 220 Ω), 1 buzzer actif
- 1 Raspberry Pi 5

| RC522 | ESP32-S3-CAM |
|---|---|
| 3.3V | 3V3 |
| GND | GND |
| SCK | GPIO 14 |
| MOSI | GPIO 21 |
| MISO | GPIO 47 |
| SDA (SS) | GPIO 41 |
| RST | GPIO 42 |

| Composant | ESP32-S3-CAM |
|---|---|
| LED verte | GPIO 1 |
| LED rouge | GPIO 2 |
| Buzzer | GPIO 3 |

> Les broches ont été choisies pour ne pas entrer en conflit avec la caméra. Elles peuvent varier selon le fabricant de la carte ESP32-S3-CAM : à vérifier avant de souder.

---

## Base de données

Base : `vaisseau_db` (script complet dans `bdd/bdd_vaisseau.sql`).

**Contrôle d'accès**

| Table | Champs |
|---|---|
| `user` | id, nom, prenom |
| `carte` | **uid** (PK, identifiant lu par le RC522), niveau, statut, id_user → user |
| `porte` | id, nom, niveau_autorisation_requis, zone, etat |

**Vaisseau et navigation** (partagé avec les autres groupes)

| Table | Champs |
|---|---|
| `vaisseau` | id, nom, x, y, z, vitesse, energie_actuelle, consommation |
| `energie` | id, vaisseau_id → vaisseau, type, puissance, capacite |
| `itineraire` | id, vaisseau_id → vaisseau, nom, distance_totale, duree, energie_necessaire, faisable |
| `etoile` | id, nom, x, y, z, puissance |
| `etape` | id, itineraire_id → itineraire, etoile_id → etoile, ordre, distance, energie_produite |

**Choix de conception**
- La carte est séparée de l'utilisateur : une personne peut changer de carte (perte, remplacement) sans perdre son identité.
- Le niveau est porté par la carte : un même membre peut avoir une carte standard et une carte « premium » avec plus de droits.
- L'UID de la puce sert directement de clé primaire, ce qui évite une correspondance supplémentaire.

---

## API

Documentation interactive générée automatiquement : `http://<ip-du-raspberry>:8000/docs`

| Méthode | Route | Rôle |
|---|---|---|
| POST | `/api/scan` | Vérifie un passage de carte (appelée par l'ESP32) |
| GET | `/api/portes` | Liste des portes |
| GET | `/api/users` | Liste des membres d'équipage |
| POST | `/api/users` | Ajoute un membre |
| GET | `/api/cartes` | Liste des cartes avec leur titulaire |
| POST | `/api/cartes` | Enregistre une carte |
| PATCH | `/api/cartes/{uid}` | Active ou désactive une carte |
| GET | `/api/historique` | 50 derniers passages |
| WS | `/ws` | Flux temps réel des passages |
| GET | `/` | Interface web |

### Contrat de `/api/scan`
Requête :
```json
{ "uid": "A1B2C3D4", "porte_id": 3 }
```
Réponse si autorisé :
```json
{ "autorise": true, "nom": "Durand", "prenom": "Léa", "niveau": 3, "porte": "Poste de commande" }
```
Réponse si refusé :
```json
{ "autorise": false, "motif": "niveau_insuffisant" }
```
Motifs : `carte_inconnue`, `carte_inactive`, `niveau_insuffisant`.

---

## Installation sur le Raspberry Pi

### 1. Se connecter
```bash
ssh workshop@ESA-cyber.local
```

### 2. Installer les outils
```bash
sudo apt update
sudo apt install -y mariadb-server python3-venv unzip
```

### 3. Créer l'utilisateur MySQL
```bash
sudo mysql -e "CREATE USER 'workshop'@'localhost' IDENTIFIED BY 'mdp'; GRANT ALL PRIVILEGES ON vaisseau_db.* TO 'workshop'@'localhost'; FLUSH PRIVILEGES;"
```
Les identifiants doivent correspondre à ceux de `api/db.py`.

### 4. Récupérer le projet
Depuis le Git :
```bash
git clone <url-du-depot> horizon2080
```
ou depuis un PC (PowerShell) :
```powershell
scp horizon2080.zip workshop@ESA-cyber.local:~
```
puis sur le Raspberry : `unzip horizon2080.zip`

### 5. Créer la base
```bash
cd ~/horizon2080
sudo mysql < bdd/bdd_vaisseau.sql
sudo mysql < bdd/donnees_test.sql
```
> Attention : `bdd_vaisseau.sql` supprime la base `vaisseau_db` si elle existe déjà.

### 6. Lancer l'API
```bash
cd api
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

Pour la laisser tourner après la déconnexion SSH :
```bash
nohup uvicorn main:app --host 0.0.0.0 --port 8000 > api.log 2>&1 &
```
Arrêter : `pkill -f uvicorn` — Voir les logs : `tail -f api.log`

### 7. Ouvrir l'interface
`http://ESA-cyber.local:8000` (ou `http://<ip-du-raspberry>:8000`)

L'IP du Raspberry s'obtient avec `hostname -I`.

---

## Configuration de l'ESP32

1. Dans l'IDE Arduino, installer le support des cartes **ESP32** et sélectionner **ESP32S3 Dev Module**.
2. Installer les bibliothèques **MFRC522** et **ArduinoJson** (v7).
3. Dans `esp32/lecteur_porte.ino`, modifier :
```cpp
const char* WIFI_SSID = "NOM_DU_WIFI";
const char* WIFI_PASS = "MOT_DE_PASSE";
const char* API_URL   = "http://<ip-du-raspberry>:8000/api/scan";
const int   PORTE_ID  = 1;   // id de la porte simulée (1 à 4)
```
> Utiliser l'**IP** du Raspberry et non `ESA-cyber.local` : l'ESP32 ne résout pas les noms en `.local`.

4. Téléverser, puis ouvrir le moniteur série (115200 bauds) : chaque carte passée affiche son UID.

---

## Scénario de démonstration

Données de test : **Léa Durand** et **Hugo Petit**, et 4 portes (Quartiers équipage niv. 1, Infirmerie niv. 1, Laboratoire niv. 2, Poste de commande niv. 3).

1. Passer la **carte premium** : inconnue, la porte passe au rouge et l'interface propose de l'enregistrer → l'associer à Léa, **niveau 3**.
2. Passer le **porte-clé** → l'associer à Hugo, **niveau 1**.
3. Devant le **poste de commande** : la carte premium passe (vert), le porte-clé est refusé (*Niveau insuffisant*).
4. **Désactiver** une carte depuis le tableau : elle est refusée partout.

Sans matériel, le bloc **« Simuler un passage »** de l'interface produit exactement le même résultat (plan B en cas de panne pendant la démo).

---

## Limites de la V1 et pistes V2

| Limite actuelle | Amélioration prévue |
|---|---|
| Historique des passages gardé en mémoire (perdu au redémarrage de l'API) | Table de logs en base, chaînée par hash pour la rendre infalsifiable |
| Pas de double authentification | Zones sensibles avec vérification faciale (caméra de l'ESP32-S3-CAM) ou empreinte |
| Mot de passe MySQL en clair dans `db.py` | Variables d'environnement, mot de passe robuste |
| Serveur injoignable = porte bloquée | Cache local des droits sur l'ESP32 pour fonctionner hors ligne |
| Pas de gestion de crise | Modes urgence (ouverture des zones vitales) et confinement |
| Aucune détection d'anomalie | Alertes sur les tentatives répétées, les cartes clonées ou les horaires inhabituels |
| L'API se lance à la main | Service `systemd` démarré automatiquement avec le Raspberry |
