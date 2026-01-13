# """
# Script d'initialisation — crée le compte Administrateur par défaut.
# Exécuter une seule fois : python seed.py

# IMPORTANT : Changez le mot de passe admin immédiatement après la première connexion.
# """
# import sys
# import os
# sys.path.insert(0, os.path.dirname(__file__))

# from dotenv import load_dotenv
# load_dotenv()

# from werkzeug.security import generate_password_hash
# import pymysql
# from config import Config

# DEFAULT_PASSWORD = os.environ.get('ADMIN_DEFAULT_PASSWORD', 'Admin@AR2025!')

# def seed():
#     conn = pymysql.connect(
#         host=Config.DB_HOST,
#         user=Config.DB_USER,
#         password=Config.DB_PASSWORD,
#         database=Config.DB_NAME,
#         charset='utf8mb4'
#     )
#     cur = conn.cursor()

#     admin = {
#         'nom':          'Mariem',
#         'prenom':       'Brahim',
#         'email':        'houdabrahum@gmail.com',
#         'telephone':    '',
#         'mot_de_passe': generate_password_hash(DEFAULT_PASSWORD),
#         'role':         'administrateur',
#     }

#     cur.execute("SELECT id_utilisateur FROM utilisateur WHERE email=%s", (admin['email'],))
#     if cur.fetchone():
#         print("✓ Compte administrateur déjà présent.")
#     else:
#         cur.execute("""
#             INSERT INTO utilisateur (nom, prenom, email, telephone, mot_de_passe, role)
#             VALUES (%(nom)s, %(prenom)s, %(email)s, %(telephone)s, %(mot_de_passe)s, %(role)s)
#         """, admin)
#         conn.commit()
#         print(f"✓ Administrateur créé : {admin['email']}")
#         print(f"  Mot de passe : {DEFAULT_PASSWORD}")
#         print("  ⚠ Changez ce mot de passe dès la première connexion.")

#     cur.close()
#     conn.close()

# if __name__ == '__main__':
#     seed()
