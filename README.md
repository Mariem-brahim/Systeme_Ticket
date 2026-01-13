# Système de Suivi des Tickets — Autorité de Régulation

Application intranet Flask/MySQL pour la gestion et le suivi des tickets techniques.

---

## Prérequis

- Python 3.10+
- MySQL 8.x
- pip

---

## Installation

### 1. Installer les dépendances Python

```bash
pip install -r requirements.txt
```

### 2. Créer la base de données

Connectez-vous à MySQL et exécutez le script SQL :

```bash
mysql -u root -p < schema.sql
```

### 3. Configurer la connexion (optionnel)

Par défaut : `root` / pas de mot de passe / base `gestion_tickets` sur `localhost`.

Pour personnaliser, définissez les variables d'environnement :

```bash
export DB_HOST=localhost
export DB_USER=root
export DB_PASSWORD=votre_mot_de_passe
export DB_NAME=gestion_tickets
export SECRET_KEY=une_cle_secrete_longue
```

### 4. Créer le compte Administrateur par défaut

```bash
python seed.py
```

Compte créé :
- **Email :** houdabrahum@gmail.com
- **Mot de passe :** 1234

### 5. Lancer l'application

```bash
python run.py
```

Accès : [http://localhost:5000](http://localhost:5000)

---

## Structure du projet

```
ticket_system/
├── run.py                    # Point d'entrée
├── config.py                 # Configuration
├── db.py                     # Connexion MySQL
├── seed.py                   # Initialisation administrateur
├── schema.sql                # Schéma base de données
├── requirements.txt
└── app/
    ├── __init__.py           # Factory Flask
    ├── decorators.py         # login_required, role_required
    ├── auth/                 # Authentification + OTP
    ├── utilisateur/          # Création/suivi de tickets
    ├── technicien/           # Prise en charge et résolution
    ├── directeur/            # Tableau de bord / statistiques
    ├── admin/                # Gestion des comptes
    ├── static/
    │   ├── css/main.css
    │   ├── js/main.js
    │   └── img/logo.png
    └── templates/
        ├── base.html
        ├── auth/
        ├── utilisateur/
        ├── technicien/
        ├── directeur/
        └── admin/
```

---

## Rôles et accès

| Rôle           | Fonctionnalités                                             |
|----------------|-------------------------------------------------------------|
| Utilisateur    | Créer des tickets, suivre l'avancement, valider, évaluer    |
| Technicien     | Consulter, prendre en charge, commenter, résoudre           |
| Directeur      | Tableau de bord statistique (lecture seule)                 |
| Administrateur | Créer / modifier / supprimer des comptes                    |

---

## Notes de sécurité

- Les mots de passe sont hachés via `werkzeug.security.generate_password_hash` (PBKDF2-SHA256).
- L'authentification utilise un code OTP à 6 chiffres envoyé par email (en développement : affiché dans la console).
- Les routes sont protégées par des décorateurs `login_required` et `role_required`.
