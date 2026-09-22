# Contexte du projet — Workshop EPSI B3 « Horizon 2080 »

## Le workshop
- Workshop national EPSI Bachelor 3 (septembre 2026), 4 jours, soutenance le vendredi.
- Thème : on est la R&D de l'ESA et on conçoit des briques technologiques pour le premier vaisseau interstellaire (le « Yggdrasil »).
- Équipe de 7 : un groupe HumanTech et un groupe cyber (4 personnes) qui fait le **système de carte d'accès du vaisseau**. Un autre groupe (AgriTech) partage la base de données.
- Livrables : dossier technique PDF, présentation PPTX, code (zip ou GitHub).
- Règle importante : l'IA peut aider à coder, mais **chaque membre doit pouvoir expliquer chaque ligne du code** devant le jury. Privilégier un code simple, lisible et commenté en français.
- Critères du jury : pertinence, prototype fonctionnel, innovation, **résilience / maintenabilité**, qualité de la présentation.

## Le projet : carte d'accès du vaisseau (V1)
Un astronaute passe son badge RFID devant le lecteur d'une porte. Le système compare le niveau de la carte avec le niveau requis par la porte et ouvre ou refuse.

### Décisions prises pour la V1 (ne pas les remettre en cause sans qu'on le demande)
- **Pas de zones sensibles** et pas de vérification faciale en V1 (prévu en V2 avec la caméra).
- **Pas de table de logs** pour l'instant (solution à trouver, piste : petite table `log_acces`).
- **Pas de blocage de carte** après des échecs répétés.
- La table `carte` est **séparée** de `user`. L'identifiant de la carte est l'**UID RFID** lui-même.
- Le **niveau est porté par la carte** (idée de la carte « premium » avec plus de droits).
- Règle d'accès V1 : `carte.statut = 'active'` ET `carte.niveau >= porte.niveau_autorisation_requis`.
- Serveur injoignable → la porte reste fermée (fail-secure).
- Idées pour la V2 : zones sensibles + biométrie, journal de logs chaîné par hash, modes de crise (urgence, confinement), révocation de carte, détection de clonage.

## Matériel disponible
- 1 **ESP32-S3-CAM** (un seul microcontrôleur, il gère le lecteur ET la caméra)
- 1 lecteur **RFID RC522** (alimenté en **3,3 V uniquement**, communication SPI)
- 1 badge porte-clé + 1 carte « premium »
- LED verte, LED rouge, buzzer

### Câblage prévu (à vérifier selon le modèle exact de la carte ESP32-S3-CAM)
| RC522 | ESP32-S3-CAM |
|---|---|
| 3.3V | 3V3 |
| GND | GND |
| SCK | GPIO 14 |
| MOSI | GPIO 21 |
| MISO | GPIO 47 |
| SDA (SS) | GPIO 41 |
| RST | GPIO 42 |

LED verte → GPIO 1, LED rouge → GPIO 2, buzzer → GPIO 3 (LED avec résistance 220 Ω).

## Stack technique
| Partie | Techno |
|---|---|
| API | Python + FastAPI |
| Accès BDD | mysql-connector (requêtes SQL simples, explicables) |
| Base | MySQL 8 |
| Webapp | React |
| Temps réel | WebSocket FastAPI |
| Firmware | Arduino C++ (MFRC522 + ArduinoJson v7) |

## Architecture
```
[Badge] → [ESP32-S3-CAM + RC522] --POST /api/scan--> [API FastAPI] <--> [MySQL]
                                                          |
                                                    WebSocket
                                                          v
                                                   [Webapp React]
```
L'API est le point central. L'ESP32 et la webapp ne se parlent pas directement (sauf plus tard pour afficher le flux vidéo de la caméra via `http://<ip-esp32>:81/stream`).

Tous les appareils doivent être sur le **même réseau Wi-Fi** (partage de connexion d'un téléphone conseillé, le Wi-Fi de l'école bloque souvent les appareils entre eux).

## Contrat d'API (à respecter, les collègues codent en parallèle dessus)

### Scan d'un badge — ESP32 → API
```
POST /api/scan
{ "uid": "A1B2C3D4", "porte_id": 3 }
```
Réponse si autorisé :
```
{ "autorise": true, "nom": "Durand", "prenom": "Léa", "niveau": 3, "porte": "Poste de commande" }
```
Réponse si refusé :
```
{ "autorise": false, "motif": "niveau_insuffisant" }
```
Motifs possibles : `carte_inconnue`, `carte_inactive`, `niveau_insuffisant`.

Chaque scan doit aussi être envoyé en temps réel à la webapp (WebSocket).

### Enregistrement d'une nouvelle carte
On passe la carte sur le lecteur, l'API reçoit un UID inconnu, et la webapp le propose directement dans le formulaire de création de carte.

## Base de données (schéma validé par l'équipe)
Le script complet est dans `bdd/bdd_vaisseau.sql`.

```
user        (id PK, nom, prenom)
carte       (uid PK VARCHAR, niveau, statut, id_user FK -> user.id)
porte       (id PK, nom, niveau_autorisation_requis, zone, etat)

vaisseau    (id PK, nom, x, y, z, vitesse, energie_actuelle, consommation)
energie     (id PK, vaisseau_id FK, type, puissance, capacite)
itineraire  (id PK, vaisseau_id FK, nom, distance_totale, duree, energie_necessaire, faisable)
etoile      (id PK, nom, x, y, z, puissance)
etape       (id PK, itineraire_id FK, etoile_id FK, ordre, distance, energie_produite)
```
Note : `user` est un mot-clé SQL, toujours l'écrire entre backticks : `` `user` ``.

## Webapp (fonctionnalités prévues)
- Plan du vaisseau avec les portes (vert/rouge en direct à chaque scan)
- Flux des derniers passages
- Gestion des users et des cartes (création d'une carte en scannant le badge)
- **Mode simulation sans matériel** : choisir une carte et une porte dans l'interface pour simuler un scan (plan B en cas de panne pendant la démo)

## Structure du projet visée
```
horizon2080/
├── api/          # FastAPI (main.py, db.py, requirements.txt)
├── webapp/       # React
├── esp32/        # lecteur_porte.ino
└── bdd/          # bdd_vaisseau.sql
```

## Travail en parallèle
- Un collègue développe une fonction Python liée à la lecture de l'UID de la carte → à intégrer dans l'API.
- Un collègue travaille sur l'ESP32-S3-CAM (caméra, résolution…).
- Moi : l'API et la webapp.
Adapter le code existant des collègues plutôt que de le réécrire, et signaler toute incohérence avec le contrat d'API ci-dessus.

## Style attendu
- Réponses en français, ton informel, concises et structurées.
- Code simple et commenté en français, sans sur-ingénierie : c'est un prototype en 4 jours.
