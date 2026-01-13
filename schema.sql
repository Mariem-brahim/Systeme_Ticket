-- ============================================================
-- Base de données : gestion_tickets
-- Autorité de Régulation — Système de suivi des tickets
-- ============================================================

DROP DATABASE IF EXISTS gestion_tickets;

CREATE DATABASE gestion_tickets
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE gestion_tickets;

-- ============================================================
-- TABLE : utilisateur
-- ============================================================

CREATE TABLE utilisateur (
    id_utilisateur INT AUTO_INCREMENT PRIMARY KEY,
    nom            VARCHAR(100) NOT NULL,
    prenom         VARCHAR(100) NOT NULL,
    email          VARCHAR(150) NOT NULL UNIQUE,
    mot_de_passe   VARCHAR(256) NOT NULL,
    telephone      VARCHAR(20),

    role ENUM(
        'utilisateur',
        'technicien',
        'directeur',
        'administrateur'
    ) NOT NULL DEFAULT 'utilisateur',

    actif          TINYINT(1) NOT NULL DEFAULT 1,
    date_creation  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- TABLE : technicien
-- ============================================================

CREATE TABLE technicien (
    id_utilisateur INT PRIMARY KEY,

    specialite ENUM(
        'Réseaux',
        'Sécurité',
        'Système',
        'Support'
    ) NOT NULL,

    note_moyenne   DECIMAL(3,2) NOT NULL DEFAULT 0.00,
    nb_evaluations INT NOT NULL DEFAULT 0,

    FOREIGN KEY (id_utilisateur)
        REFERENCES utilisateur(id_utilisateur)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- TABLE : ticket
-- ============================================================

CREATE TABLE ticket (
    id_ticket INT AUTO_INCREMENT PRIMARY KEY,

    titre       VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,

    statut ENUM(
        'Soumise',
        'En_cours',
        'En_attente',
        'Résolu',
        'Réouvert',
        'Clôturé'
    ) NOT NULL DEFAULT 'Soumise',

    categorie ENUM(
        'Matériel',
        'Logiciel',
        'Réseau',
        'Sécurité',
        'Compte/accés'
    ) NOT NULL,

    priorite ENUM(
        'Haute',
        'Moyenne',
        'Faible'
    ) NOT NULL DEFAULT 'Moyenne',

    date_creation   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    date_resolution DATETIME DEFAULT NULL,
    date_cloture    DATETIME DEFAULT NULL,

    cree_par  INT NOT NULL,
    assigne_a INT DEFAULT NULL,

    FOREIGN KEY (cree_par)
        REFERENCES utilisateur(id_utilisateur)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,

    FOREIGN KEY (assigne_a)
        REFERENCES technicien(id_utilisateur)
        ON DELETE SET NULL
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- TABLE : historique_ticket
-- ============================================================

CREATE TABLE historique_ticket (
    id_historique INT AUTO_INCREMENT PRIMARY KEY,

    id_ticket INT NOT NULL,

    ancien_statut ENUM(
        'Soumise',
        'En_cours',
        'En_attente',
        'Résolu',
        'Réouvert',
        'Clôturé'
    ) DEFAULT NULL,

    nouveau_statut ENUM(
        'Soumise',
        'En_cours',
        'En_attente',
        'Résolu',
        'Réouvert',
        'Clôturé'
    ) NOT NULL,

    date_changement DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    change_par INT DEFAULT NULL,

    est_systeme TINYINT(1) NOT NULL DEFAULT 0,

    commentaire_log VARCHAR(500) DEFAULT NULL,

    FOREIGN KEY (id_ticket)
        REFERENCES ticket(id_ticket)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    FOREIGN KEY (change_par)
        REFERENCES utilisateur(id_utilisateur)
        ON DELETE SET NULL
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- TABLE : commentaire
-- ============================================================

CREATE TABLE commentaire (
    id_commentaire INT AUTO_INCREMENT PRIMARY KEY,

    texte TEXT NOT NULL,

    date_creation DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    id_ticket INT NOT NULL,
    ecrit_par INT NOT NULL,

    FOREIGN KEY (id_ticket)
        REFERENCES ticket(id_ticket)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    FOREIGN KEY (ecrit_par)
        REFERENCES technicien(id_utilisateur)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- TABLE : evaluation
-- ============================================================

CREATE TABLE evaluation (
    id_evaluation INT AUTO_INCREMENT PRIMARY KEY,

    note TINYINT NOT NULL CHECK (note BETWEEN 1 AND 5),

    feedback TEXT,

    date_eval DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    id_utilisateur INT NOT NULL,

    id_ticket INT NOT NULL UNIQUE,

    FOREIGN KEY (id_utilisateur)
        REFERENCES utilisateur(id_utilisateur)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    FOREIGN KEY (id_ticket)
        REFERENCES ticket(id_ticket)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- TABLE : verification_email
-- ============================================================

CREATE TABLE verification_email (
    id INT AUTO_INCREMENT PRIMARY KEY,

    email VARCHAR(150) NOT NULL,

    code VARCHAR(10) NOT NULL,

    expire_le DATETIME NOT NULL,

    utilise TINYINT(1) NOT NULL DEFAULT 0,

    tentatives TINYINT NOT NULL DEFAULT 0,

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_email_code (email, code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- TABLE : notification
-- ============================================================

CREATE TABLE notification (
    id_notification INT AUTO_INCREMENT PRIMARY KEY,

    id_utilisateur INT NOT NULL,

    message VARCHAR(500) NOT NULL,

    lu TINYINT(1) NOT NULL DEFAULT 0,

    id_ticket INT DEFAULT NULL,

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (id_utilisateur)
        REFERENCES utilisateur(id_utilisateur)
        ON DELETE CASCADE,

    FOREIGN KEY (id_ticket)
        REFERENCES ticket(id_ticket)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- TABLE : proposition_ticket
-- ============================================================

CREATE TABLE proposition_ticket (
    id_proposition INT AUTO_INCREMENT PRIMARY KEY,

    id_ticket INT NOT NULL,

    id_technicien INT NOT NULL,

    statut ENUM(
        'en_attente',
        'acceptée',
        'refusée'
    ) NOT NULL DEFAULT 'en_attente',

    date_creation DATETIME DEFAULT CURRENT_TIMESTAMP,

    date_reponse DATETIME DEFAULT NULL,

    FOREIGN KEY (id_ticket)
        REFERENCES ticket(id_ticket)
        ON DELETE CASCADE,

    FOREIGN KEY (id_technicien)
        REFERENCES technicien(id_utilisateur)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- TRIGGERS
-- ============================================================

DELIMITER $$

CREATE TRIGGER trg_ticket_date_resolution
BEFORE UPDATE ON ticket
FOR EACH ROW
BEGIN

    IF NEW.statut = 'Résolu'
       AND OLD.statut != 'Résolu' THEN

        SET NEW.date_resolution = NOW();

    END IF;

    IF NEW.statut = 'Clôturé'
       AND OLD.statut != 'Clôturé' THEN

        SET NEW.date_cloture = NOW();

    END IF;

    IF NEW.statut NOT IN ('Résolu','Clôturé') THEN

        SET NEW.date_resolution = NULL;

    END IF;

END$$

CREATE TRIGGER trg_ticket_log_historique
AFTER UPDATE ON ticket
FOR EACH ROW
BEGIN

    IF OLD.statut != NEW.statut THEN

        INSERT INTO historique_ticket (
            id_ticket,
            ancien_statut,
            nouveau_statut,
            est_systeme
        )
        VALUES (
            NEW.id_ticket,
            OLD.statut,
            NEW.statut,
            1
        );

    END IF;

END$$

CREATE TRIGGER trg_update_note_technicien
AFTER INSERT ON evaluation
FOR EACH ROW
BEGIN

    DECLARE tech_id INT;

    SELECT assigne_a
    INTO tech_id
    FROM ticket
    WHERE id_ticket = NEW.id_ticket;

    IF tech_id IS NOT NULL THEN

        UPDATE technicien
        SET
            note_moyenne = (
                SELECT AVG(e.note)
                FROM evaluation e
                JOIN ticket t
                    ON e.id_ticket = t.id_ticket
                WHERE t.assigne_a = tech_id
            ),

            nb_evaluations = (
                SELECT COUNT(*)
                FROM evaluation e
                JOIN ticket t
                    ON e.id_ticket = t.id_ticket
                WHERE t.assigne_a = tech_id
            )

        WHERE id_utilisateur = tech_id;

    END IF;

END$$

DELIMITER ;

-- ============================================================
-- INDEX
-- ============================================================

CREATE INDEX idx_ticket_statut
ON ticket(statut);

CREATE INDEX idx_ticket_priorite
ON ticket(priorite);

CREATE INDEX idx_ticket_categorie
ON ticket(categorie);

CREATE INDEX idx_ticket_cree_par
ON ticket(cree_par);

CREATE INDEX idx_ticket_assigne_a
ON ticket(assigne_a);

CREATE INDEX idx_prop_ticket
ON proposition_ticket(id_ticket, statut);

CREATE INDEX idx_prop_tech
ON proposition_ticket(id_technicien, statut);