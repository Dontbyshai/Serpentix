-- ============================================================
-- Serpentix — Schéma de la base de données SQLite
-- Projet NSI : site web dynamique + jeu 1v1
-- ============================================================

-- Table des utilisateurs (joueurs inscrits)
CREATE TABLE IF NOT EXISTS utilisateurs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pseudo TEXT NOT NULL UNIQUE,               -- nom affiché en jeu
    email TEXT NOT NULL UNIQUE,                -- adresse e-mail unique
    mot_de_passe_hash TEXT NOT NULL,          -- mot de passe haché (Werkzeug)
    couleur_skin TEXT NOT NULL DEFAULT '#ffffff', -- skin équipé (hex)
    skins_debloques TEXT NOT NULL DEFAULT 'blanc', -- ids séparés par virgules
    coins INTEGER NOT NULL DEFAULT 0,          -- monnaie gagnée en jouant
    est_admin INTEGER NOT NULL DEFAULT 0,     -- conservé pour CRUD NSI (caché UI)
    date_inscription TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- Table des parties (une salle de jeu 1v1)
CREATE TABLE IF NOT EXISTS parties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,                -- code à 6 caractères pour rejoindre
    statut TEXT NOT NULL DEFAULT 'attente',   -- attente | en_cours | terminee
    createur_id INTEGER NOT NULL,             -- joueur qui a créé la salle
    vainqueur_id INTEGER,                     -- NULL tant que la partie n'est pas finie
    date_creation TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    date_fin TEXT,
    -- Si le créateur supprime son compte, ses parties sont supprimées aussi
    FOREIGN KEY (createur_id) REFERENCES utilisateurs(id) ON DELETE CASCADE,
    -- Si le vainqueur supprime son compte, on garde la partie sans vainqueur
    FOREIGN KEY (vainqueur_id) REFERENCES utilisateurs(id) ON DELETE SET NULL
);

-- Table des participations / scores (lien N-N utilisateurs ↔ parties)
CREATE TABLE IF NOT EXISTS participations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    utilisateur_id INTEGER NOT NULL,
    partie_id INTEGER NOT NULL,
    score INTEGER NOT NULL DEFAULT 0,         -- pommes mangées / points
    a_gagne INTEGER NOT NULL DEFAULT 0,       -- 1 si vainqueur
    FOREIGN KEY (utilisateur_id) REFERENCES utilisateurs(id) ON DELETE CASCADE,
    FOREIGN KEY (partie_id) REFERENCES parties(id) ON DELETE CASCADE,
    UNIQUE (utilisateur_id, partie_id)
);

-- Index : accélèrent les recherches (comme l'index d'un livre)
CREATE INDEX IF NOT EXISTS idx_participations_score ON participations(score DESC);
CREATE INDEX IF NOT EXISTS idx_parties_code ON parties(code);
