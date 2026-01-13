# """
# Script de données de démonstration — Autorité de Régulation
# =============================================================
# Crée un jeu de données complet pour tester et présenter le système.

# Comptes créés (domaine @demo.mr — aucune restriction dans le code) :
# ┌─────────────────────────────────────────────────────────────┐
# │ Rôle          │ Email                    │ Mot de passe     │
# ├───────────────┼──────────────────────────┼──────────────────┤
# │ Administrateur│ admin@demo.mr            │ Admin@AR2025!    │
# │ Directeur     │ directeur@demo.mr        │ Demo@AR2025!     │
# │ Technicien    │ tech.reseau@demo.mr      │ Demo@AR2025!     │
# │ Technicien    │ tech.support@demo.mr     │ Demo@AR2025!     │
# │ Utilisateur   │ alice.ndiaye@demo.mr     │ Demo@AR2025!     │
# │ Utilisateur   │ omar.ba@demo.mr          │ Demo@AR2025!     │
# │ Utilisateur   │ fatou.diallo@demo.mr     │ Demo@AR2025!     │
# └─────────────────────────────────────────────────────────────┘

# CONNEXION : puisque SMTP n'est pas configuré, le code OTP s'affiche
#             directement à l'écran après soumission du formulaire de connexion.

# Usage :
#     python seed_demo.py          # insère si absent, ignore si déjà présent
#     python seed_demo.py --reset  # supprime tout et recrée depuis zéro
# """

# import sys
# import os
# sys.path.insert(0, os.path.dirname(__file__))

# from dotenv import load_dotenv
# load_dotenv()

# from werkzeug.security import generate_password_hash
# import pymysql
# from config import Config
# from datetime import datetime, timedelta
# import random

# # ── Mot de passe commun pour tous les comptes de démo ──────────────────────
# MDP_ADMIN = '123456'
# MDP_DEMO  = 'Demo@AR2025!'


# def get_conn():
#     return pymysql.connect(
#         host=Config.DB_HOST, user=Config.DB_USER,
#         password=Config.DB_PASSWORD, database=Config.DB_NAME,
#         charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor,
#         autocommit=False
#     )


# def reset(conn):
#     """Supprime toutes les données dans le bon ordre (FK)."""
#     cur = conn.cursor()
#     tables = [
#         'proposition_ticket', 'notification', 'evaluation',
#         'commentaire', 'historique_ticket', 'ticket',
#         'technicien', 'verification_email', 'utilisateur',
#     ]
#     cur.execute("SET FOREIGN_KEY_CHECKS = 0")
#     for t in tables:
#         cur.execute(f"TRUNCATE TABLE {t}")
#     cur.execute("SET FOREIGN_KEY_CHECKS = 1")
#     conn.commit()
#     print("✓ Base de données réinitialisée.")


# def insert_user(cur, conn, nom, prenom, email, telephone, role, mdp):
#     cur.execute("SELECT id_utilisateur FROM utilisateur WHERE email=%s", (email,))
#     row = cur.fetchone()
#     if row:
#         return row['id_utilisateur']
#     cur.execute("""
#         INSERT INTO utilisateur (nom, prenom, email, telephone, mot_de_passe, role, actif)
#         VALUES (%s,%s,%s,%s,%s,%s,1)
#     """, (nom, prenom, email, telephone, generate_password_hash(mdp), role))
#     conn.commit()
#     return cur.lastrowid


# def insert_technicien(cur, conn, uid, specialite):
#     cur.execute("SELECT id_utilisateur FROM technicien WHERE id_utilisateur=%s", (uid,))
#     if not cur.fetchone():
#         cur.execute(
#             "INSERT INTO technicien (id_utilisateur, specialite) VALUES (%s,%s)",
#             (uid, specialite)
#         )
#         conn.commit()


# def insert_ticket(cur, conn, titre, description, categorie, priorite,
#                   cree_par, assigne_a, statut, jours_avant=None):
#     """Insère un ticket avec une date simulée dans le passé."""
#     if jours_avant is None:
#         jours_avant = random.randint(1, 60)
#     date_creation = datetime.now() - timedelta(days=jours_avant,
#                                                 hours=random.randint(0, 12))
#     cur.execute("""
#         INSERT INTO ticket (titre, description, categorie, priorite, cree_par,
#                             assigne_a, statut, date_creation)
#         VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
#     """, (titre, description, categorie, priorite, cree_par,
#           assigne_a, statut, date_creation))
#     conn.commit()
#     tid = cur.lastrowid

#     # Historique initial
#     cur.execute("""
#         INSERT INTO historique_ticket (id_ticket, nouveau_statut, change_par,
#                                         est_systeme, commentaire_log, date_changement)
#         VALUES (%s,'Soumise',%s,0,'Ticket créé',%s)
#     """, (tid, cree_par, date_creation))

#     if assigne_a and statut != 'Soumise':
#         date_assign = date_creation + timedelta(hours=random.randint(1, 6))
#         cur.execute("""
#             INSERT INTO historique_ticket (id_ticket, ancien_statut, nouveau_statut,
#                                             change_par, est_systeme, date_changement)
#             VALUES (%s,'Soumise','En_cours',%s,0,%s)
#         """, (tid, assigne_a, date_assign))
#         cur.execute(
#             "UPDATE ticket SET statut=%s WHERE id_ticket=%s",
#             (statut, tid)
#         )

#     if statut in ('Résolu', 'Clôturé'):
#         date_res = date_creation + timedelta(days=random.randint(1, 3))
#         cur.execute(
#             "UPDATE ticket SET date_resolution=%s WHERE id_ticket=%s",
#             (date_res, tid)
#         )
#         cur.execute("""
#             INSERT INTO historique_ticket (id_ticket, ancien_statut, nouveau_statut,
#                                             change_par, est_systeme, date_changement)
#             VALUES (%s,'En_cours','Résolu',%s,0,%s)
#         """, (tid, assigne_a, date_res))
#         if statut == 'Clôturé':
#             date_clo = date_res + timedelta(hours=random.randint(2, 12))
#             cur.execute(
#                 "UPDATE ticket SET date_cloture=%s, statut='Clôturé' WHERE id_ticket=%s",
#                 (date_clo, tid)
#             )
#             cur.execute("""
#                 INSERT INTO historique_ticket (id_ticket, ancien_statut, nouveau_statut,
#                                                 change_par, est_systeme, date_changement)
#                 VALUES (%s,'Résolu','Clôturé',%s,0,%s)
#             """, (tid, cree_par, date_clo))

#     conn.commit()
#     return tid


# def add_commentaire(cur, conn, tid, texte, ecrit_par):
#     cur.execute(
#         "INSERT INTO commentaire (texte, id_ticket, ecrit_par) VALUES (%s,%s,%s)",
#         (texte, tid, ecrit_par)
#     )
#     conn.commit()


# def add_evaluation(cur, conn, tid, id_utilisateur, note, feedback):
#     cur.execute("SELECT id_evaluation FROM evaluation WHERE id_ticket=%s", (tid,))
#     if not cur.fetchone():
#         cur.execute("""
#             INSERT INTO evaluation (note, feedback, id_utilisateur, id_ticket)
#             VALUES (%s,%s,%s,%s)
#         """, (note, feedback, id_utilisateur, tid))
#         conn.commit()


# def seed_demo():
#     conn = get_conn()
#     cur  = conn.cursor()

#     if '--reset' in sys.argv:
#         reset(conn)

#     print("\n── Création des comptes ──────────────────────────────────")

#     # Administrateur
#     uid_admin = insert_user(cur, conn,
#         'Mariem', 'Brahim', 'houdabrahum@gmail.com', '', 'administrateur', MDP_ADMIN)
#     print(f"  ✓ Administrateur  → houdabrahum@gmail.com")

#     # Directeur
#     uid_dir = insert_user(cur, conn,
#         'Sow', 'Mamadou', 'directeur@demo.mr', '+222 36 10 00 01', 'directeur', MDP_DEMO)
#     print(f"  ✓ Directeur       → directeur@demo.mr")

#     # Techniciens
#     uid_t1 = insert_user(cur, conn,
#         'Diallo', 'Ibrahima', 'tech.reseau@demo.mr', '+222 36 10 00 02', 'technicien', MDP_DEMO)
#     insert_technicien(cur, conn, uid_t1, 'Réseaux')
#     print(f"  ✓ Technicien      → tech.reseau@demo.mr  (Réseaux)")

#     uid_t2 = insert_user(cur, conn,
#         'Mint Brahim', 'Mariem', 'tech.support@demo.mr', '+222 36 10 00 03', 'technicien', MDP_DEMO)
#     insert_technicien(cur, conn, uid_t2, 'Support')
#     print(f"  ✓ Technicien      → tech.support@demo.mr (Support)")

#     # Utilisateurs
#     uid_u1 = insert_user(cur, conn,
#         'Ndiaye', 'Alice', 'alice.ndiaye@demo.mr', '+222 36 10 00 10', 'utilisateur', MDP_DEMO)
#     print(f"  ✓ Utilisateur     → alice.ndiaye@demo.mr")

#     uid_u2 = insert_user(cur, conn,
#         'Ba', 'Omar', 'omar.ba@demo.mr', '+222 36 10 00 11', 'utilisateur', MDP_DEMO)
#     print(f"  ✓ Utilisateur     → omar.ba@demo.mr")

#     uid_u3 = insert_user(cur, conn,
#         'Diallo', 'Fatou', 'fatou.diallo@demo.mr', '+222 36 10 00 12', 'utilisateur', MDP_DEMO)
#     print(f"  ✓ Utilisateur     → fatou.diallo@demo.mr")

#     print("\n── Création des tickets de démo ──────────────────────────")

#     # ── Tickets CLÔTURÉS (avec évaluations) ───────────────────────────────────
#     t1 = insert_ticket(cur, conn,
#         titre="Imprimante réseau hors service — salle de conférence",
#         description="L'imprimante HP LaserJet du 2e étage ne répond plus depuis ce matin. "
#                     "Le voyant clignote en orange. Aucun poste ne peut s'y connecter.",
#         categorie='Matériel', priorite='Haute',
#         cree_par=uid_u1, assigne_a=uid_t2, statut='Clôturé', jours_avant=45)
#     add_commentaire(cur, conn, t1,
#         "Problème identifié : file d'impression corrompue.\n"
#         "Redémarrage du spouleur d'impression + vidage de la file. "
#         "Imprimante opérationnelle à 14h30.",
#         uid_t2)
#     add_evaluation(cur, conn, t1, uid_u1, 5,
#         "Intervention rapide et efficace. Problème réglé en moins de 2 heures.")

#     t2 = insert_ticket(cur, conn,
#         titre="Mot de passe oublié — accès bloqué après 5 tentatives",
#         description="Je n'arrive plus à me connecter au portail RH. Mon compte semble verrouillé.",
#         categorie='Comptabilité', priorite='Moyenne',
#         cree_par=uid_u2, assigne_a=uid_t2, statut='Clôturé', jours_avant=30)
#     add_commentaire(cur, conn, t2,
#         "Compte déverrouillé et nouveau mot de passe provisoire communiqué par email sécurisé.",
#         uid_t2)
#     add_evaluation(cur, conn, t2, uid_u2, 4,
#         "Rapide, mais j'aurais apprécié une explication sur la politique de mots de passe.")

#     t3 = insert_ticket(cur, conn,
#         titre="Perte de connectivité WiFi — bureau direction",
#         description="Depuis la mise à jour du routeur vendredi, le réseau WiFi du bureau de "
#                     "direction est instable. Déconnexions toutes les 20-30 minutes environ.",
#         categorie='Réseau', priorite='Haute',
#         cree_par=uid_u3, assigne_a=uid_t1, statut='Clôturé', jours_avant=20)
#     add_commentaire(cur, conn, t3,
#         "Mise à jour du firmware du point d'accès TP-Link annulée (rollback v2.1.4).\n"
#         "Test de stabilité sur 24h : aucune déconnexion constatée.",
#         uid_t1)
#     add_evaluation(cur, conn, t3, uid_u3, 5,
#         "Excellent diagnostic. Le technicien a identifié le problème sans perturber le travail.")

#     t4 = insert_ticket(cur, conn,
#         titre="Écran noir au démarrage — PC bureau comptabilité",
#         description="L'ordinateur du bureau 214 ne démarre plus correctement. "
#                     "Écran noir après le logo BIOS. Windows ne se charge pas.",
#         categorie='Matériel', priorite='Haute',
#         cree_par=uid_u1, assigne_a=uid_t2, statut='Clôturé', jours_avant=15)
#     add_commentaire(cur, conn, t4,
#         "Disque dur défaillant (secteurs corrompus détectés). "
#         "Remplacement du SSD + restauration depuis sauvegarde réseau. "
#         "Données récupérées à 98%.",
#         uid_t2)
#     add_evaluation(cur, conn, t4, uid_u1, 4, "Bonne intervention, mais délai un peu long.")

#     # ── Tickets EN COURS ──────────────────────────────────────────────────────
#     t5 = insert_ticket(cur, conn,
#         titre="Logiciel de paie plante à l'ouverture",
#         description="Le logiciel Sage Paie affiche une erreur 'Runtime Error 217' dès le "
#                     "lancement depuis ce matin. Cela bloque la clôture mensuelle.",
#         categorie='Logiciel', priorite='Haute',
#         cree_par=uid_u2, assigne_a=uid_t2, statut='En_cours', jours_avant=2)
#     add_commentaire(cur, conn, t5,
#         "En cours d'investigation. Piste : conflit avec la mise à jour Windows KB5034441 "
#         "installée hier soir. Vérification en cours.",
#         uid_t2)

#     t6 = insert_ticket(cur, conn,
#         titre="Câble réseau débranché — salle serveurs",
#         description="Un câble réseau dans la baie 3 de la salle serveurs semble débranché "
#                     "suite aux travaux de vendredi. Deux postes du 3e étage n'ont plus accès.",
#         categorie='Réseau', priorite='Moyenne',
#         cree_par=uid_u3, assigne_a=uid_t1, statut='En_cours', jours_avant=1)

#     # ── Tickets SOUMIS (non assignés) ─────────────────────────────────────────
#     t7 = insert_ticket(cur, conn,
#         titre="Accès VPN impossible depuis télétravail",
#         description="Impossible de me connecter au VPN de l'organisation depuis chez moi. "
#                     "L'application Cisco AnyConnect affiche : 'Unable to contact the VPN server'.",
#         categorie='Réseau', priorite='Haute',
#         cree_par=uid_u1, assigne_a=None, statut='Soumise', jours_avant=0)

#     t8 = insert_ticket(cur, conn,
#         titre="Mise à jour Microsoft Office refusée",
#         description="La mise à jour Office 365 vers la version 2401 échoue sur mon poste "
#                     "avec le code erreur 0x80070005 (accès refusé).",
#         categorie='Logiciel', priorite='Faible',
#         cree_par=uid_u2, assigne_a=None, statut='Soumise', jours_avant=0)

#     # ── Ticket RÉOUVERT ───────────────────────────────────────────────────────
#     t9 = insert_ticket(cur, conn,
#         titre="Scanner réseau — qualité dégradée après intervention",
#         description="Le scanner HP du service courrier fonctionne mais les fichiers produits "
#                     "sont flous depuis la dernière intervention. Résolution réduite à 72 dpi "
#                     "au lieu de 300 dpi.",
#         categorie='Matériel', priorite='Moyenne',
#         cree_par=uid_u3, assigne_a=None, statut='Réouvert', jours_avant=5)

#     print(f"  ✓ {9} tickets créés (4 clôturés, 2 en cours, 2 soumis, 1 réouvert)")

#     # Déclenchement des propositions automatiques pour les tickets non assignés
#     print("\n── Propositions automatiques ─────────────────────────────")
#     try:
#         from app.auto_assign import proposer_ticket
#         for tid, cat in [(t7, 'Réseau'), (t8, 'Logiciel'), (t9, 'Matériel')]:
#             ok = proposer_ticket(conn, tid, cat)
#             if ok:
#                 print(f"  ✓ Ticket #{tid} proposé automatiquement")
#             else:
#                 print(f"  ⚠ Ticket #{tid} : aucun technicien éligible (normal en démo)")
#     except Exception as e:
#         print(f"  ⚠ Auto-assign ignoré : {e}")

#     cur.close()
#     conn.close()

#     print("\n" + "═" * 60)
#     print("  DONNÉES DE DÉMONSTRATION PRÊTES")
#     print("═" * 60)
#     print()
#     print("  Rôle           Email                      Mot de passe")
#     print("  ─────────────  ─────────────────────────  ─────────────")
#     print(f"  Administrateur admin@demo.mr               {MDP_ADMIN}")
#     print(f"  Directeur      directeur@demo.mr           {MDP_DEMO}")
#     print(f"  Technicien     tech.reseau@demo.mr         {MDP_DEMO}")
#     print(f"  Technicien     tech.support@demo.mr        {MDP_DEMO}")
#     print(f"  Utilisateur    alice.ndiaye@demo.mr        {MDP_DEMO}")
#     print(f"  Utilisateur    omar.ba@demo.mr             {MDP_DEMO}")
#     print(f"  Utilisateur    fatou.diallo@demo.mr        {MDP_DEMO}")
#     print()
#     print("  ⚠ SMTP non requis : le code OTP s'affiche à l'écran.")
#     print("  ⚠ Aucune restriction de domaine email dans le système.")
#     print("═" * 60)


# if __name__ == '__main__':
#     seed_demo()
