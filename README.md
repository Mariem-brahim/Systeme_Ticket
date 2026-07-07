# Système de Suivi des Tickets — Autorité de Régulation

Application web interne (intranet) de gestion des incidents informatiques, développée avec **Flask** et **MySQL**.

Les employés déclarent leurs incidents (matériel, logiciel, réseau, sécurité, comptes/accès). Le système **propose automatiquement** chaque ticket au technicien le plus adapté, qui le traite et le résout. L'employé valide ensuite la résolution et évalue le service, pendant que le directeur suit l'activité via un tableau de bord statistique et des rapports PDF.

---

## Fonctionnalités

- **Authentification à deux étapes** : mot de passe + code OTP à 6 chiffres envoyé par email (valable 10 minutes, 3 tentatives max).
- **Affectation automatique intelligente** : chaque nouveau ticket est proposé au technicien le plus adapté — spécialité correspondant à la catégorie, meilleure note, charge la plus faible. En cas de refus, le ticket passe au technicien suivant ; s'il n'y a personne, le directeur est alerté.
- **Cycle de vie complet du ticket** :
  `Soumise → En_cours → Résolu → Clôturé` (avec `En_attente` et `Réouvert` si l'employé refuse la résolution).
- **Notifications internes** en temps quasi réel (badge mis à jour toutes les 30 s).
- **Évaluation des techniciens** : note de 1 à 5 étoiles après clôture, moyenne visible par le directeur.
- **Tableau de bord directeur** : statistiques par statut / priorité / catégorie, temps moyen de résolution, top techniciens, évolution sur 6 mois — exportables en **rapport PDF officiel** avec en-tête bilingue français/arabe.
- **Administration des comptes** : création, modification, activation/désactivation des utilisateurs.

## Rôles

| Rôle           | Ce qu'il peut faire                                                        |
|----------------|-----------------------------------------------------------------------------|
| Utilisateur    | Créer des tickets, suivre l'avancement, valider ou refuser la résolution, évaluer |
| Technicien     | Accepter/refuser les propositions, prendre en charge, commenter, résoudre   |
| Directeur      | Consulter les statistiques, générer les rapports PDF (lecture seule)        |
| Administrateur | Gérer les comptes (création, modification, rôles, désactivation)            |

## Technologies

Python 3.10+ · Flask 3 · MySQL 8 (PyMySQL) · Flask-WTF (CSRF) · ReportLab (PDF) · HTML/CSS/JS sans framework front.

## Notes de sécurité

- Mots de passe hachés avec `werkzeug.security` (PBKDF2-SHA256) — jamais stockés en clair.
- Toutes les requêtes SQL sont paramétrées (protection contre l'injection SQL).
- Protection CSRF activée sur tous les formulaires (Flask-WTF).
- Routes protégées par les décorateurs `login_required` et `role_required`.
