-- =====================================================================
--  Workshop Horizon 2080 - BDD du vaisseau (schéma de l'équipe v4)
--  MySQL 8
-- =====================================================================

DROP DATABASE IF EXISTS vaisseau_db;
CREATE DATABASE vaisseau_db CHARACTER SET utf8mb4;
USE vaisseau_db;

-- ------------------------- CONTRÔLE D'ACCÈS -------------------------

CREATE TABLE `user` (
    id      INT AUTO_INCREMENT PRIMARY KEY,
    nom     VARCHAR(100) NOT NULL,
    prenom  VARCHAR(100) NOT NULL
);

-- UID = identifiant lu par le RC522 (ex : 'A1B2C3D4')
CREATE TABLE carte (
    uid      VARCHAR(32) PRIMARY KEY,
    niveau   INT NOT NULL,
    statut   VARCHAR(20) NOT NULL DEFAULT 'active',
    id_user  INT NOT NULL,
    FOREIGN KEY (id_user) REFERENCES `user`(id)
);

CREATE TABLE porte (
    id                          INT AUTO_INCREMENT PRIMARY KEY,
    nom                         VARCHAR(100) NOT NULL,
    niveau_autorisation_requis  INT NOT NULL,
    zone                        VARCHAR(100) NOT NULL,
    etat                        VARCHAR(50) NOT NULL
);

-- ------------------------- VAISSEAU / ÉNERGIE -----------------------

CREATE TABLE vaisseau (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    nom              VARCHAR(100) NOT NULL,
    x                FLOAT NOT NULL DEFAULT 0,
    y                FLOAT NOT NULL DEFAULT 0,
    z                FLOAT NOT NULL DEFAULT 0,
    vitesse          FLOAT NOT NULL DEFAULT 0,
    energie_actuelle FLOAT NOT NULL DEFAULT 0,
    consommation     FLOAT NOT NULL DEFAULT 0
);

CREATE TABLE energie (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    vaisseau_id  INT NOT NULL,
    type         VARCHAR(50) NOT NULL,
    puissance    FLOAT NOT NULL,
    capacite     FLOAT NOT NULL,
    FOREIGN KEY (vaisseau_id) REFERENCES vaisseau(id)
);

-- ------------------------- NAVIGATION -------------------------------

CREATE TABLE itineraire (
    id                 INT AUTO_INCREMENT PRIMARY KEY,
    vaisseau_id        INT NOT NULL,
    nom                VARCHAR(100) NOT NULL,
    distance_totale    FLOAT NOT NULL,
    duree              FLOAT NOT NULL,
    energie_necessaire FLOAT NOT NULL,
    faisable           BOOLEAN NOT NULL DEFAULT FALSE,
    FOREIGN KEY (vaisseau_id) REFERENCES vaisseau(id)
);

CREATE TABLE etoile (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    nom        VARCHAR(100) NOT NULL,
    x          FLOAT NOT NULL,
    y          FLOAT NOT NULL,
    z          FLOAT NOT NULL,
    puissance  FLOAT NOT NULL
);

CREATE TABLE etape (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    itineraire_id   INT NOT NULL,
    etoile_id       INT NOT NULL,
    ordre           INT NOT NULL,
    distance        FLOAT NOT NULL,
    energie_produite FLOAT NOT NULL,
    FOREIGN KEY (itineraire_id) REFERENCES itineraire(id),
    FOREIGN KEY (etoile_id)     REFERENCES etoile(id)
);
