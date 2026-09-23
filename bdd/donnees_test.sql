-- Données de test pour la démo V1
-- À lancer APRÈS bdd_vaisseau.sql
USE vaisseau_db;

INSERT INTO `user` (nom, prenom) VALUES
('Durand', 'Léa'),     -- commandante
('Petit',  'Hugo');    -- membre d'équipage

INSERT INTO porte (nom, niveau_autorisation_requis, zone, etat) VALUES
('Observatoire',                         0, 'Couloir blanc', 'fermee'),
('Équipage A',                           0, 'Couloir blanc', 'fermee'),
('Équipage B',                           0, 'Couloir blanc', 'fermee'),
('Centre médical',                       0, 'Couloir blanc', 'fermee'),
('Unité psy',                            0, 'Couloir blanc', 'fermee'),
('SAS 1',                                1, 'Couloir blanc', 'fermee'),
('Serre Hydro A',                        1, 'Couloir vert',  'fermee'),
('Serre Hydro B',                        1, 'Couloir vert',  'fermee'),
('Recyclage Eau',                        1, 'Couloir vert',  'fermee'),
('SAS 2',                                2, 'Couloir vert',  'fermee'),
('Générateur principal A',               2, 'Couloir jaune', 'fermee'),
('Générateur principal B',               2, 'Couloir jaune', 'fermee'),
('Escalier nord',                         2, 'Couloir jaune', 'fermee'),
('Escalier sud',                          2, 'Couloir jaune', 'fermee'),
('Escalier est',                          2, 'Couloir jaune', 'fermee'),
('Stockage A',                            2, 'Couloir jaune', 'fermee'),
('Stockage B',                            2, 'Couloir jaune', 'fermee'),
('Moteur A',                              2, 'Couloir jaune', 'fermee'),
('Moteur B',                              2, 'Couloir jaune', 'fermee'),
('SAS blindé',                            3, 'Couloir jaune', 'fermee'),
('Poste sécurité & armurerie A',         3, 'Couloir rouge',  'fermee'),
('Poste sécurité & armurerie B',         3, 'Couloir rouge',  'fermee'),
('Commandement',                          3, 'Couloir rouge',  'fermee'),
('Serveur IA',                             3, 'Couloir rouge',  'fermee'),
('Serveur de secours',                    3, 'Couloir rouge',  'fermee');

-- Les cartes s'ajoutent depuis l'interface : on passe le badge sur le lecteur,
-- l'UID apparaît et on l'associe à un user.
-- Ou à la main, en remplaçant par les vrais UID lus dans le moniteur série :
-- INSERT INTO carte (uid, niveau, statut, id_user) VALUES ('UID_CARTE_PREMIUM', 3, 'active', 1);
-- INSERT INTO carte (uid, niveau, statut, id_user) VALUES ('UID_PORTE_CLE',     1, 'active', 2);
