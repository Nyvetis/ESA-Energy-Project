# ESA-Energy-Project

## Système de contrôle d'accès

Projet réalisé dans le cadre du *Workshop Horizon 2080*.

> Ce projet consiste à créer un système de contrôle d'accès sécurisé avec une carte Arduino, un lecteur RFID, une caméra pour vérification à deux facteurs (vérifié par un humain via une interface) et des cartes d'accès.

## Fonctionnement

L'utilisateur présente sa carte RFID devant le lecteur :

* Carte autorisée → l'accès est mis en attente et la caméra liée au est activée pour la vérification à deux facteurs.
* Carte de niveau inférieur à la porte
* Carte inconnue → l'accès est refusé.

>Le système permet ainsi de simuler la sécurisation des différentes zones d'un vaisseau spatial.

## Technologies utilisées

* Arduino
* Module RFID
* Cartes RFID
* Module de 3 LEDs (rouge jaune et vert)

## Objectif

>L'objectif est de mettre en place une solution simple de contrôle d'accès pouvant être intégrée au système de cybersécurité du vaisseau.


## Schéma de la base de données
<img width="1452" height="675" alt="image" src="https://github.com/user-attachments/assets/d12be734-b146-43b3-a7be-5f0a648956c2" />

### Autres schémas/images du projet
<img width="1795" height="1348" alt="Flowchart Whiteboard in Grey Lilac Blue Simple and Minimal Style(1)" src="https://github.com/user-attachments/assets/96986020-169b-4b46-86fb-56819e9b44a8" />
<img width="2606" height="3908" alt="Flowchart Whiteboard in Grey Lilac Blue Simple and Minimal Style" src="https://github.com/user-attachments/assets/d5d37ce6-dea7-4e3c-a09a-560ae4071a56" />

<img width="8905" height="2597" alt="Flowchart Whiteboard in Grey Lilac Blue Simple and Minimal Style(2)" src="https://github.com/user-attachments/assets/b47af0b1-b4ef-4575-bb7a-b02abd2e82f1" />
