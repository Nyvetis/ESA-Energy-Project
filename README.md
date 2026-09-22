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