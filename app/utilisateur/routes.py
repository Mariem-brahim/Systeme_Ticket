from flask import render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash
from app.utilisateur import bp
from app.decorators import login_required, role_required
from app.helpers import creer_notification, get_notifications, count_non_lues, marquer_lues
import db as database


@bp.route('/dashboard')
@login_required
@role_required('utilisateur')
def dashboard():
    db  = database.get_db()
    cur = db.cursor()
    uid = session['user_id']
    cur.execute("""
        SELECT t.*, CONCAT(u.prenom,' ',u.nom) AS technicien_nom
        FROM ticket t LEFT JOIN utilisateur u ON u.id_utilisateur = t.assigne_a
        WHERE t.cree_par = %s ORDER BY t.date_creation DESC
    """, (uid,))
    tickets = cur.fetchall()
    stats = {s: sum(1 for t in tickets if t['statut'] == s)
             for s in ('Soumise', 'En_cours', 'En_attente', 'Résolu', 'Réouvert', 'Clôturé')}
    nb_notifs = count_non_lues(uid)
    return render_template('utilisateur/dashboard.html', tickets=tickets,
                           stats=stats, nb_notifs=nb_notifs)


@bp.route('/creer-ticket', methods=['GET', 'POST'])
@login_required
@role_required('utilisateur')
def creer_ticket():
    if request.method == 'POST':
        titre       = request.form.get('titre', '').strip()
        description = request.form.get('description', '').strip()
        categorie   = request.form.get('categorie', '')
        priorite    = request.form.get('priorite', '')

        CATEGORIES_OK = ('Matériel', 'Logiciel', 'Réseau', 'Sécurité', 'Compte/accès')
        PRIORITES_OK  = ('Haute', 'Moyenne', 'Faible')

        if not titre or not description or categorie not in CATEGORIES_OK or priorite not in PRIORITES_OK:
            flash('Tous les champs sont obligatoires et doivent être valides.', 'danger')
            return render_template('utilisateur/creer_ticket.html')
        if len(titre) > 255:
            flash('Le titre ne peut pas dépasser 255 caractères.', 'danger')
            return render_template('utilisateur/creer_ticket.html')

        db  = database.get_db()
        cur = db.cursor()
        try:
            cur.execute("""
                INSERT INTO ticket (titre, description, categorie, priorite, cree_par, statut)
                VALUES (%s, %s, %s, %s, %s, 'Soumise')
            """, (titre, description, categorie, priorite, session['user_id']))
            tid = cur.lastrowid
            cur.execute("""
                INSERT INTO historique_ticket (id_ticket, nouveau_statut, change_par, est_systeme, commentaire_log)
                VALUES (%s, 'Soumise', %s, 0, 'Ticket créé')
            """, (tid, session['user_id']))
            db.commit()
        except Exception:
            db.rollback()
            flash("Erreur lors de la création du ticket. Veuillez réessayer.", 'danger')
            return render_template('utilisateur/creer_ticket.html')

        # Déclencher l'affectation automatique
        try:
            from app.auto_assign import proposer_ticket
            proposer_ticket(db, tid, categorie)
        except Exception:
            pass  # L'auto-affectation est non-bloquante

        flash('Ticket créé avec succès. Un technicien sera notifié automatiquement.', 'success')
        return redirect(url_for('utilisateur.mes_tickets'))
    return render_template('utilisateur/creer_ticket.html')


@bp.route('/mes-tickets')
@login_required
@role_required('utilisateur')
def mes_tickets():
    db  = database.get_db()
    cur = db.cursor()
    statut    = request.args.get('statut', '')
    priorite  = request.args.get('priorite', '')
    categorie = request.args.get('categorie', '')
    query = """
        SELECT t.*, CONCAT(u.prenom,' ',u.nom) AS technicien_nom
        FROM ticket t LEFT JOIN utilisateur u ON u.id_utilisateur = t.assigne_a
        WHERE t.cree_par = %s
    """
    params = [session['user_id']]
    if statut:    query += " AND t.statut = %s";    params.append(statut)
    if priorite:  query += " AND t.priorite = %s";  params.append(priorite)
    if categorie: query += " AND t.categorie = %s"; params.append(categorie)
    query += " ORDER BY FIELD(t.priorite,'Haute','Moyenne','Faible'), t.date_creation DESC"
    cur.execute(query, params)
    tickets   = cur.fetchall()
    nb_notifs = count_non_lues(session['user_id'])
    return render_template('utilisateur/mes_tickets.html', tickets=tickets,
                           filtre_statut=statut, filtre_priorite=priorite,
                           filtre_categorie=categorie, nb_notifs=nb_notifs)


@bp.route('/ticket/<int:tid>')
@login_required
@role_required('utilisateur')
def detail_ticket(tid):
    db  = database.get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT t.*, CONCAT(u.prenom,' ',u.nom) AS technicien_nom
        FROM ticket t LEFT JOIN utilisateur u ON u.id_utilisateur = t.assigne_a
        WHERE t.id_ticket = %s AND t.cree_par = %s
    """, (tid, session['user_id']))
    ticket = cur.fetchone()
    if not ticket:
        flash('Ticket introuvable.', 'danger')
        return redirect(url_for('utilisateur.mes_tickets'))
    cur.execute("""
        SELECT c.texte, c.date_creation, CONCAT(u.prenom,' ',u.nom) AS auteur
        FROM commentaire c JOIN utilisateur u ON u.id_utilisateur = c.ecrit_par
        WHERE c.id_ticket = %s ORDER BY c.date_creation ASC
    """, (tid,))
    commentaires = cur.fetchall()
    cur.execute("""
        SELECT h.*, CONCAT(u.prenom,' ',u.nom) AS acteur
        FROM historique_ticket h LEFT JOIN utilisateur u ON u.id_utilisateur = h.change_par
        WHERE h.id_ticket = %s ORDER BY h.date_changement ASC
    """, (tid,))
    historique = cur.fetchall()
    cur.execute("SELECT * FROM evaluation WHERE id_ticket = %s", (tid,))
    evaluation = cur.fetchone()
    nb_notifs  = count_non_lues(session['user_id'])

    # Barre de progression — chemin réel du ticket depuis l'historique
    raw = ['Soumise'] + [h['nouveau_statut'] for h in historique]
    progress_steps = []
    for s in raw:
        if not progress_steps or progress_steps[-1] != s:
            progress_steps.append(s)

    current = ticket['statut']
    if not progress_steps or progress_steps[-1] != current:
        progress_steps.append(current)

    progress_current_idx = len(progress_steps) - 1

    can_edit = (ticket['statut'] == 'Soumise' and ticket['assigne_a'] is None)

    return render_template('utilisateur/detail_ticket.html',
                           ticket=ticket, commentaires=commentaires,
                           historique=historique, evaluation=evaluation,
                           progress_steps=progress_steps,
                           progress_current_idx=progress_current_idx,
                           can_edit=can_edit,
                           nb_notifs=nb_notifs)


@bp.route('/ticket/<int:tid>/modifier', methods=['GET', 'POST'])
@login_required
@role_required('utilisateur')
def modifier_ticket(tid):
    db  = database.get_db()
    cur = db.cursor()
    cur.execute(
        "SELECT * FROM ticket WHERE id_ticket=%s AND cree_par=%s",
        (tid, session['user_id'])
    )
    ticket = cur.fetchone()
    if not ticket:
        flash('Ticket introuvable.', 'danger')
        return redirect(url_for('utilisateur.mes_tickets'))
    if ticket['statut'] != 'Soumise' or ticket['assigne_a'] is not None:
        flash("Ce ticket ne peut plus être modifié (déjà pris en charge).", 'warning')
        return redirect(url_for('utilisateur.detail_ticket', tid=tid))

    if request.method == 'POST':
        titre       = request.form.get('titre', '').strip()
        description = request.form.get('description', '').strip()
        categorie   = request.form.get('categorie', '')
        priorite    = request.form.get('priorite', '')
        CATEGORIES_OK = ('Matériel', 'Logiciel', 'Réseau', 'Sécurité', 'Comptabilité')
        PRIORITES_OK  = ('Haute', 'Moyenne', 'Faible')
        if not titre or not description or categorie not in CATEGORIES_OK or priorite not in PRIORITES_OK:
            flash('Tous les champs sont obligatoires et valides.', 'danger')
            return render_template('utilisateur/modifier_ticket.html', ticket=ticket)
        if len(titre) > 255:
            flash('Le titre ne peut pas dépasser 255 caractères.', 'danger')
            return render_template('utilisateur/modifier_ticket.html', ticket=ticket)
        try:
            cur.execute(
                "UPDATE ticket SET titre=%s, description=%s, categorie=%s, priorite=%s "
                "WHERE id_ticket=%s AND cree_par=%s AND statut='Soumise' AND assigne_a IS NULL",
                (titre, description, categorie, priorite, tid, session['user_id'])
            )
            db.commit()
            flash('Ticket mis à jour avec succès.', 'success')
        except Exception:
            db.rollback()
            flash("Erreur lors de la mise à jour.", 'danger')
        return redirect(url_for('utilisateur.detail_ticket', tid=tid))

    return render_template('utilisateur/modifier_ticket.html', ticket=ticket)


@bp.route('/ticket/<int:tid>/supprimer', methods=['POST'])
@login_required
@role_required('utilisateur')
def supprimer_ticket(tid):
    db  = database.get_db()
    cur = db.cursor()
    cur.execute(
        "SELECT * FROM ticket WHERE id_ticket=%s AND cree_par=%s AND statut='Soumise' AND assigne_a IS NULL",
        (tid, session['user_id'])
    )
    ticket = cur.fetchone()
    if not ticket:
        flash("Ce ticket ne peut pas être supprimé (déjà pris en charge ou introuvable).", 'warning')
        return redirect(url_for('utilisateur.mes_tickets'))
    try:
        cur.execute("DELETE FROM historique_ticket WHERE id_ticket=%s", (tid,))
        cur.execute("DELETE FROM ticket WHERE id_ticket=%s AND cree_par=%s", (tid, session['user_id']))
        db.commit()
        flash('Ticket supprimé.', 'success')
    except Exception:
        db.rollback()
        flash("Erreur lors de la suppression.", 'danger')
    return redirect(url_for('utilisateur.mes_tickets'))


@bp.route('/ticket/<int:tid>/valider', methods=['POST'])
@login_required
@role_required('utilisateur')
def valider_resolution(tid):
    db  = database.get_db()
    cur = db.cursor()
    cur.execute(
        "SELECT * FROM ticket WHERE id_ticket=%s AND cree_par=%s AND statut='Résolu'",
        (tid, session['user_id'])
    )
    ticket = cur.fetchone()
    if not ticket:
        flash('Action impossible.', 'danger')
        return redirect(url_for('utilisateur.mes_tickets'))

    action = request.form.get('action')
    try:
        if action == 'valider':
            cur.execute(
                "UPDATE ticket SET statut='Clôturé', assigne_a=assigne_a WHERE id_ticket=%s",
                (tid,)
            )
            cur.execute("""
                INSERT INTO historique_ticket (id_ticket, ancien_statut, nouveau_statut, change_par, est_systeme)
                VALUES (%s, 'Résolu', 'Clôturé', %s, 0)
            """, (tid, session['user_id']))
            db.commit()
            if ticket['assigne_a']:
                creer_notification(
                    ticket['assigne_a'],
                    f"✓ Résolution validée pour le ticket #{tid} : « {ticket['titre']} ».",
                    tid
                )
            flash('Ticket clôturé avec succès.', 'success')
            return redirect(url_for('utilisateur.evaluer_ticket', tid=tid))
        else:
            # Refus : réouvrir + annuler assignation
            tech_id = ticket['assigne_a']
            cur.execute(
                "UPDATE ticket SET statut='Réouvert', assigne_a=NULL WHERE id_ticket=%s",
                (tid,)
            )
            cur.execute("""
                INSERT INTO historique_ticket (id_ticket, ancien_statut, nouveau_statut, change_par, est_systeme)
                VALUES (%s, 'Résolu', 'Réouvert', %s, 0)
            """, (tid, session['user_id']))
            db.commit()
            if tech_id:
                creer_notification(
                    tech_id,
                    f"⚠ Résolution refusée — ticket #{tid} « {ticket['titre']} » réouvert.",
                    tid
                )
            # Re-proposer automatiquement
            try:
                from app.auto_assign import proposer_ticket
                proposer_ticket(db, tid, ticket['categorie'])
            except Exception:
                pass
            flash('Ticket réouvert. Un technicien sera de nouveau notifié.', 'warning')
            return redirect(url_for('utilisateur.detail_ticket', tid=tid))
    except Exception:
        db.rollback()
        flash("Erreur lors de l'opération. Veuillez réessayer.", 'danger')
        return redirect(url_for('utilisateur.detail_ticket', tid=tid))


@bp.route('/ticket/<int:tid>/evaluer', methods=['GET', 'POST'])
@login_required
@role_required('utilisateur')
def evaluer_ticket(tid):
    db  = database.get_db()
    cur = db.cursor()
    cur.execute(
        "SELECT * FROM ticket WHERE id_ticket=%s AND cree_par=%s AND statut='Clôturé'",
        (tid, session['user_id'])
    )
    ticket = cur.fetchone()
    if not ticket:
        flash('Évaluation impossible : le ticket doit être clôturé.', 'danger')
        return redirect(url_for('utilisateur.mes_tickets'))
    cur.execute("SELECT * FROM evaluation WHERE id_ticket=%s", (tid,))
    if cur.fetchone():
        flash('Vous avez déjà évalué ce ticket.', 'info')
        return redirect(url_for('utilisateur.detail_ticket', tid=tid))
    if request.method == 'POST':
        note     = request.form.get('note', '')
        feedback = request.form.get('feedback', '').strip()
        try:
            note_int = int(note)
            if note_int not in range(1, 6):
                raise ValueError
        except (ValueError, TypeError):
            flash('Note invalide (1 à 5 étoiles requis).', 'danger')
            return render_template('utilisateur/evaluer_ticket.html', ticket=ticket)
        try:
            cur.execute(
                "INSERT INTO evaluation (note, feedback, id_utilisateur, id_ticket) "
                "VALUES (%s, %s, %s, %s)",
                (note_int, feedback, session['user_id'], tid)
            )
            db.commit()
        except Exception:
            db.rollback()
            flash("Erreur lors de l'enregistrement. Veuillez réessayer.", 'danger')
            return render_template('utilisateur/evaluer_ticket.html', ticket=ticket)
        flash('Évaluation enregistrée. Merci pour votre retour !', 'success')
        return redirect(url_for('utilisateur.detail_ticket', tid=tid))
    return render_template('utilisateur/evaluer_ticket.html', ticket=ticket)


# ── NOTIFICATIONS ─────────────────────────────────────────────────────────────

@bp.route('/notifications')
@login_required
@role_required('utilisateur')
def notifications():
    uid    = session['user_id']
    notifs = get_notifications(uid)
    marquer_lues(uid)
    return render_template('utilisateur/notifications.html', notifs=notifs, nb_notifs=0)


@bp.route('/notifications/count')
@login_required
@role_required('utilisateur')
def notif_count():
    return jsonify({'count': count_non_lues(session['user_id'])})


# ── PROFIL ────────────────────────────────────────────────────────────────────

@bp.route('/profil', methods=['GET', 'POST'])
@login_required
@role_required('utilisateur')
def profil():
    db  = database.get_db()
    cur = db.cursor()
    uid = session['user_id']
    if request.method == 'POST':
        nouvel_email = request.form.get('email', '').strip().lower()
        nom          = request.form.get('nom', '').strip()
        prenom       = request.form.get('prenom', '').strip()
        telephone    = request.form.get('telephone', '').strip()
        new_mdp      = request.form.get('mot_de_passe', '')

        if not nom or not prenom or not nouvel_email:
            flash('Les champs Nom, Prénom et Email sont obligatoires.', 'danger')
            return redirect(url_for('utilisateur.profil'))

        if nouvel_email != session['user_email']:
            cur.execute(
                "SELECT id_utilisateur FROM utilisateur "
                "WHERE email=%s AND id_utilisateur!=%s",
                (nouvel_email, uid)
            )
            if cur.fetchone():
                flash('Cet email est déjà utilisé par un autre compte.', 'danger')
                return redirect(url_for('utilisateur.profil'))

        try:
            cur.execute(
                "UPDATE utilisateur SET nom=%s, prenom=%s, email=%s, telephone=%s "
                "WHERE id_utilisateur=%s",
                (nom, prenom, nouvel_email, telephone, uid)
            )
            if new_mdp:
                if len(new_mdp) < 6:
                    flash('Le mot de passe doit contenir au moins 6 caractères.', 'danger')
                    return redirect(url_for('utilisateur.profil'))
                cur.execute(
                    "UPDATE utilisateur SET mot_de_passe=%s WHERE id_utilisateur=%s",
                    (generate_password_hash(new_mdp), uid)
                )
            db.commit()
        except Exception:
            db.rollback()
            flash("Erreur lors de la mise à jour.", 'danger')
            return redirect(url_for('utilisateur.profil'))

        session['user_email'] = nouvel_email
        session['user_nom']   = f"{prenom} {nom}"
        flash('Profil mis à jour avec succès.', 'success')
        return redirect(url_for('utilisateur.profil'))

    cur.execute("SELECT * FROM utilisateur WHERE id_utilisateur=%s", (uid,))
    user      = cur.fetchone()
    nb_notifs = count_non_lues(uid)
    return render_template('utilisateur/profil.html', user=user, nb_notifs=nb_notifs)
