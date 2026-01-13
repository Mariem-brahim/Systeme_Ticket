from flask import render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash
from app.admin import bp
from app.decorators import login_required, role_required
import db as database


@bp.route('/dashboard')
@login_required
@role_required('administrateur')
def dashboard():
    db  = database.get_db()
    cur = db.cursor()
    cur.execute("SELECT COUNT(*) as nb FROM utilisateur WHERE role='utilisateur'")
    nb_util = cur.fetchone()['nb']
    cur.execute("SELECT COUNT(*) as nb FROM technicien")
    nb_tech = cur.fetchone()['nb']
    cur.execute("SELECT COUNT(*) as nb FROM utilisateur WHERE role='directeur'")
    nb_dir = cur.fetchone()['nb']
    cur.execute("SELECT COUNT(*) as nb FROM ticket")
    nb_tickets = cur.fetchone()['nb']

    filtre_role = request.args.get('role', '').strip()
    ROLES_OK = ('utilisateur', 'technicien', 'directeur', 'administrateur')
    if filtre_role not in ROLES_OK:
        filtre_role = ''

    if filtre_role:
        cur.execute("""
            SELECT u.*, t.specialite, t.note_moyenne
            FROM utilisateur u LEFT JOIN technicien t ON t.id_utilisateur = u.id_utilisateur
            WHERE u.role = %s
            ORDER BY u.nom
        """, (filtre_role,))
    else:
        cur.execute("""
            SELECT u.*, t.specialite, t.note_moyenne
            FROM utilisateur u LEFT JOIN technicien t ON t.id_utilisateur = u.id_utilisateur
            ORDER BY u.role, u.nom
        """)
    users = cur.fetchall()
    return render_template('admin/dashboard.html',
                           users=users, nb_util=nb_util,
                           nb_tech=nb_tech, nb_dir=nb_dir,
                           nb_tickets=nb_tickets,
                           filtre_role=filtre_role)


@bp.route('/creer-utilisateur', methods=['GET', 'POST'])
@login_required
@role_required('administrateur')
def creer_utilisateur():
    if request.method == 'POST':
        nom        = request.form.get('nom', '').strip()
        prenom     = request.form.get('prenom', '').strip()
        email      = request.form.get('email', '').strip().lower()
        telephone  = request.form.get('telephone', '').strip()
        role       = request.form.get('role', '')
        mdp        = request.form.get('mot_de_passe', '')
        specialite = request.form.get('specialite', '')

        ROLES_OK = ('utilisateur', 'technicien', 'directeur', 'administrateur')
        if not all([nom, prenom, email, role, mdp]) or role not in ROLES_OK:
            flash('Tous les champs obligatoires doivent être remplis.', 'danger')
            return render_template('admin/creer_utilisateur.html')
        if len(mdp) < 6:
            flash('Le mot de passe doit contenir au moins 6 caractères.', 'danger')
            return render_template('admin/creer_utilisateur.html')

        db  = database.get_db()
        cur = db.cursor()
        cur.execute("SELECT id_utilisateur FROM utilisateur WHERE email=%s", (email,))
        if cur.fetchone():
            flash('Cet email est déjà utilisé.', 'danger')
            return render_template('admin/creer_utilisateur.html')

        try:
            hashed = generate_password_hash(mdp)
            cur.execute("""
                INSERT INTO utilisateur (nom, prenom, email, telephone, mot_de_passe, role)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (nom, prenom, email, telephone, hashed, role))
            uid = cur.lastrowid

            if role == 'technicien':
                SPECIALITES_OK = ('Réseaux', 'Sécurité', 'Système', 'Support')
                if specialite not in SPECIALITES_OK:
                    raise ValueError('Spécialité invalide.')
                cur.execute(
                    "INSERT INTO technicien (id_utilisateur, specialite) VALUES (%s, %s)",
                    (uid, specialite)
                )
            db.commit()
            flash(f'Utilisateur {prenom} {nom} créé avec succès.', 'success')
            return redirect(url_for('admin.dashboard'))
        except ValueError as e:
            db.rollback()
            flash(str(e), 'danger')
            return render_template('admin/creer_utilisateur.html')
        except Exception:
            db.rollback()
            flash("Erreur lors de la création. Veuillez réessayer.", 'danger')
            return render_template('admin/creer_utilisateur.html')

    return render_template('admin/creer_utilisateur.html')


@bp.route('/modifier-utilisateur/<int:uid>', methods=['GET', 'POST'])
@login_required
@role_required('administrateur')
def modifier_utilisateur(uid):
    db  = database.get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT u.*, t.specialite
        FROM utilisateur u LEFT JOIN technicien t ON t.id_utilisateur = u.id_utilisateur
        WHERE u.id_utilisateur=%s
    """, (uid,))
    user = cur.fetchone()
    if not user:
        flash('Utilisateur introuvable.', 'danger')
        return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        nom        = request.form.get('nom', '').strip()
        prenom     = request.form.get('prenom', '').strip()
        email      = request.form.get('email', '').strip().lower()
        telephone  = request.form.get('telephone', '').strip()
        new_role   = request.form.get('role', '').strip()
        actif      = 1 if request.form.get('actif') else 0
        specialite = request.form.get('specialite', '').strip()
        new_mdp    = request.form.get('mot_de_passe', '')

        ROLES_OK      = ('utilisateur', 'technicien', 'directeur', 'administrateur')
        SPECIALITES_OK = ('Réseaux', 'Sécurité', 'Système', 'Support')

        if not nom or not prenom or not email or new_role not in ROLES_OK:
            flash('Nom, prénom, email et rôle sont obligatoires.', 'danger')
            return render_template('admin/modifier_utilisateur.html', user=user)

        # Vérifier unicité email si modifié
        if email != user['email']:
            cur.execute(
                "SELECT id_utilisateur FROM utilisateur WHERE email=%s AND id_utilisateur!=%s",
                (email, uid)
            )
            if cur.fetchone():
                flash('Cet email est déjà utilisé par un autre compte.', 'danger')
                return render_template('admin/modifier_utilisateur.html', user=user)

        if new_role == 'technicien' and specialite not in SPECIALITES_OK:
            flash('Spécialité invalide pour un technicien.', 'danger')
            return render_template('admin/modifier_utilisateur.html', user=user)

        try:
            cur.execute("""
                UPDATE utilisateur
                SET nom=%s, prenom=%s, email=%s, telephone=%s, role=%s, actif=%s
                WHERE id_utilisateur=%s
            """, (nom, prenom, email, telephone, new_role, actif, uid))

            if new_mdp:
                if len(new_mdp) < 6:
                    flash('Le mot de passe doit contenir au moins 6 caractères.', 'danger')
                    return render_template('admin/modifier_utilisateur.html', user=user)
                cur.execute(
                    "UPDATE utilisateur SET mot_de_passe=%s WHERE id_utilisateur=%s",
                    (generate_password_hash(new_mdp), uid)
                )

            old_role = user['role']
            # Gérer la table technicien selon les changements de rôle
            if old_role == 'technicien' and new_role != 'technicien':
                cur.execute("DELETE FROM technicien WHERE id_utilisateur=%s", (uid,))
            elif old_role != 'technicien' and new_role == 'technicien':
                cur.execute(
                    "INSERT INTO technicien (id_utilisateur, specialite) VALUES (%s, %s)",
                    (uid, specialite)
                )
            elif old_role == 'technicien' and new_role == 'technicien':
                cur.execute(
                    "UPDATE technicien SET specialite=%s WHERE id_utilisateur=%s",
                    (specialite, uid)
                )

            db.commit()
            flash('Utilisateur mis à jour.', 'success')
            return redirect(url_for('admin.dashboard'))
        except Exception:
            db.rollback()
            flash("Erreur lors de la mise à jour.", 'danger')
            return render_template('admin/modifier_utilisateur.html', user=user)

    return render_template('admin/modifier_utilisateur.html', user=user)


@bp.route('/supprimer-utilisateur/<int:uid>', methods=['POST'])
@login_required
@role_required('administrateur')
def supprimer_utilisateur(uid):
    if uid == session['user_id']:
        flash('Vous ne pouvez pas supprimer votre propre compte.', 'danger')
        return redirect(url_for('admin.dashboard'))
    db  = database.get_db()
    cur = db.cursor()
    try:
        cur.execute("DELETE FROM utilisateur WHERE id_utilisateur=%s", (uid,))
        db.commit()
        flash('Utilisateur supprimé.', 'success')
    except Exception:
        db.rollback()
        flash("Impossible de supprimer cet utilisateur (tickets associés actifs).", 'danger')
    return redirect(url_for('admin.dashboard'))
