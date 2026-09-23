-- Données de test pour la démo V1
-- À lancer APRÈS bdd_vaisseau.sql
USE vaisseau_db;

INSERT INTO `user` (nom, prenom) VALUES
('Durand', 'Léa'),     -- commandante
('Petit',  'Hugo');    -- membre d'équipage

INSERT INTO porte (nom, niveau_autorisation_requis, zone, etat) VALUES
('Quartiers équipage', 1, 'Habitat',      'fermee'),
('Infirmerie',         1, 'Médical',      'fermee'),
('Laboratoire',        2, 'Science',      'fermee'),
('Poste de commande',  3, 'Commandement', 'fermee');

-- Les cartes s'ajoutent depuis l'interface : on passe le badge sur le lecteur,
-- l'UID apparaît et on l'associe à un user.
-- Ou à la main, en remplaçant par les vrais UID lus dans le moniteur série :
-- INSERT INTO carte (uid, niveau, statut, id_user) VALUES ('UID_CARTE_PREMIUM', 3, 'active', 1);
-- INSERT INTO carte (uid, niveau, statut, id_user) VALUES ('UID_PORTE_CLE',     1, 'active', 2);
