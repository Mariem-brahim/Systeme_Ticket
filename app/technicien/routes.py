from flask import render_template, request, redirect, url_for, session, flash, jsonify
from app.technicien import bp
from app.decorators import login_required, role_required
from app.helpers import creer_notification, get_notifications, count_non_lues, marquer_lues
import db as database

# Transitions autorisées depuis modifier_statut (technicien assigné)
TRANSITIONS_VALIDES = {
    'En_cours':   ('En_attente',),
    'En_attente': ('En_cours',),
}


@bp.route('/dashboard')
@login_required
@role_required('technicien')
def dashboard():
    db  = database.get_db()
    cur = db.cursor()
    uid = session['user_id']

    cur.execute("""
        SELECT t.*, CONCAT(u.prenom,' ',u.nom) AS utilisateur_nom
        FROM ticket t JOIN utilisateur u ON u.id_utilisateur = t.cree_par
        WHERE t.assigne_a=%s AND t.statut='En_cours'
        ORDER BY FIELD(t.priorite,'Haute','Moyenne','Faible'), t.date_creation ASC
    """, (uid,))
    mes_tickets = cur.fetchall()

    cur.execute("SELECT specialite FROM technicien WHERE id_utilisateur=%s", (uid,))
    tech = cur.fetchone()

    cur.execute("""
        SELECT t.*, CONCAT(u.prenom,' ',u.nom) AS utilisateur_nom
        FROM ticket t JOIN utilisateur u ON u.id_utilisateur = t.cree_par
        WHERE t.statut IN ('Soumise','Réouvert','En_attente') AND t.assigne_a IS NULL
        ORDER BY FIELD(t.priorite,'Haute','Moyenne','Faible'), t.date_creation ASC LIMIT 10
    """)
    disponibles = cur.fetchall()

    # Propositions automatiques en attente pour ce technicien
    cur.execute("""
        SELECT p.id_proposition, t.id_ticket, t.titre, t.categorie, t.priorite,
               CONCAT(u.prenom,' ',u.nom) AS createur
        FROM proposition_ticket p
        JOIN ticket t ON t.id_ticket = p.id_ticket
        JOIN utilisateur u ON u.id_utilisateur = t.cree_par
        WHERE p.id_technicien = %s AND p.statut = 'en_attente'
          AND t.statut IN ('Soumise','Réouvert','En_attente') AND t.assigne_a IS NULL
        ORDER BY t.date_creation ASC
    """, (uid,))
    propositions = cur.fetchall()

    cur.execute(
        "SELECT statut, COUNT(*) as nb FROM ticket WHERE assigne_a=%s GROUP BY statut",
        (uid,)
    )
    stats = {r['statut']: r['nb'] for r in cur.fetchall()}

    cur.execute(
        "SELECT note_moyenne, nb_evaluations FROM technicien WHERE id_utilisateur=%s",
        (uid,)
    )
    perf      = cur.fetchone()
    nb_notifs = count_non_lues(uid)

    return render_template('technicien/dashboard.html',
                           mes_tickets=mes_tickets, disponibles=disponibles,
                           propositions=propositions, stats=stats, perf=perf,
                           specialite=tech['specialite'] if tech else None,
                           nb_notifs=nb_notifs)


@bp.route('/tickets-disponibles')
@login_required
@role_required('technicien')
def tickets_disponibles():
    db  = database.get_db()
    cur = db.cursor()
    statut    = request.args.get('statut', '')
    priorite  = request.args.get('priorite', '')
    categorie = request.args.get('categorie', '')
    query = """
        SELECT t.*, CONCAT(u.prenom,' ',u.nom) AS utilisateur_nom
        FROM ticket t JOIN utilisateur u ON u.id_utilisateur = t.cree_par
        WHERE t.statut IN ('Soumise','Réouvert','En_attente') AND t.assigne_a IS NULL
    """
    params = []
    if statut:    query += " AND t.statut=%s";    params.append(statut)
    if priorite:  query += " AND t.priorite=%s";  params.append(priorite)
    if categorie: query += " AND t.categorie=%s"; params.append(categorie)
    query += " ORDER BY FIELD(t.priorite,'Haute','Moyenne','Faible'), t.date_creation ASC"
    cur.execute(query, params)
    tickets   = cur.fetchall()
    nb_notifs = count_non_lues(session['user_id'])
    return render_template('technicien/tickets_disponibles.html', tickets=tickets,
                           filtre_statut=statut, filtre_priorite=priorite,
                           filtre_categorie=categorie, nb_notifs=nb_notifs)


@bp.route('/ticket/<int:tid>')
@login_required
@role_required('technicien')
def detail_ticket(tid):
    db  = database.get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT t.*, CONCAT(u.prenom,' ',u.nom) AS utilisateur_nom
        FROM ticket t JOIN utilisateur u ON u.id_utilisateur = t.cree_par
        WHERE t.id_ticket=%s
    """, (tid,))
    ticket = cur.fetchone()
    if not ticket:
        flash('Ticket introuvable.', 'danger')
        return redirect(url_for('technicien.tickets_disponibles'))
    cur.execute("""
        SELECT c.texte, c.date_creation, CONCAT(u.prenom,' ',u.nom) AS auteur
        FROM commentaire c JOIN utilisateur u ON u.id_utilisateur = c.ecrit_par
        WHERE c.id_ticket=%s ORDER BY c.date_creation ASC
    """, (tid,))
    commentaires = cur.fetchall()
    cur.execute("""
        SELECT h.*, CONCAT(u.prenom,' ',u.nom) AS acteur
        FROM historique_ticket h LEFT JOIN utilisateur u ON u.id_utilisateur = h.change_par
        WHERE h.id_ticket=%s ORDER BY h.date_changement ASC
    """, (tid,))
    historique = cur.fetchall()

    # Proposition en attente pour ce technicien sur ce ticket
    uid = session['user_id']
    cur.execute("""
        SELECT id_proposition FROM proposition_ticket
        WHERE id_ticket=%s AND id_technicien=%s AND statut='en_attente'
    """, (tid, uid))
    proposition = cur.fetchone()

    nb_notifs = count_non_lues(uid)
    return render_template('technicien/detail_ticket.html',
                           ticket=ticket, commentaires=commentaires,
                           historique=historique, proposition=proposition,
                           nb_notifs=nb_notifs)


# ── ASSIGNATION MANUELLE ─────────────────────────────────────────────────────

@bp.route('/ticket/<int:tid>/assigner', methods=['POST'])
@login_required
@role_required('technicien')
def assigner_ticket(tid):
    db  = database.get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT * FROM ticket WHERE id_ticket=%s
          AND statut IN ('Soumise','Réouvert','En_attente') AND assigne_a IS NULL
    """, (tid,))
    ticket = cur.fetchone()
    if not ticket:
        flash("Ce ticket n'est plus disponible.", 'warning')
        return redirect(url_for('technicien.tickets_disponibles'))
    uid = session['user_id']
    try:
        cur.execute(
            "UPDATE ticket SET assigne_a=%s, statut='En_cours' WHERE id_ticket=%s",
            (uid, tid)
        )
        cur.execute("""
            INSERT INTO historique_ticket (id_ticket, ancien_statut, nouveau_statut, change_par, est_systeme)
            VALUES (%s, %s, 'En_cours', %s, 0)
        """, (tid, ticket['statut'], uid))
        # Annuler toute proposition en attente sur ce ticket
        cur.execute(
            "UPDATE proposition_ticket SET statut='refusée', date_reponse=NOW() "
            "WHERE id_ticket=%s AND statut='en_attente' AND id_technicien != %s",
            (tid, uid)
        )
        cur.execute(
            "UPDATE proposition_ticket SET statut='acceptée', date_reponse=NOW() "
            "WHERE id_ticket=%s AND statut='en_attente' AND id_technicien = %s",
            (tid, uid)
        )
        db.commit()
        creer_notification(
            ticket['cree_par'],
            f"🔧 Votre ticket #{tid} « {ticket['titre']} » est pris en charge.",
            tid
        )
        flash('Ticket assigné avec succès.', 'success')
    except Exception:
        db.rollback()
        flash("Erreur lors de l'assignation.", 'danger')
    return redirect(url_for('technicien.detail_ticket', tid=tid))


# ── PROPOSITIONS AUTOMATIQUES ─────────────────────────────────────────────────

@bp.route('/ticket/<int:tid>/accepter-proposition', methods=['POST'])
@login_required
@role_required('technicien')
def accepter_proposition(tid):
    db  = database.get_db()
    cur = db.cursor()
    uid = session['user_id']

    cur.execute("""
        SELECT p.id_proposition, t.titre, t.statut, t.assigne_a, t.categorie, t.cree_par
        FROM proposition_ticket p JOIN ticket t ON t.id_ticket = p.id_ticket
        WHERE p.id_ticket=%s AND p.id_technicien=%s AND p.statut='en_attente'
    """, (tid, uid))
    row = cur.fetchone()
    if not row or row['assigne_a'] is not None or row['statut'] not in ('Soumise', 'En_attente', 'Réouvert'):
        flash("Cette proposition n'est plus valide.", 'warning')
        return redirect(url_for('technicien.dashboard'))

    try:
        cur.execute(
            "UPDATE proposition_ticket SET statut='acceptée', date_reponse=NOW() "
            "WHERE id_proposition=%s",
            (row['id_proposition'],)
        )
        cur.execute(
            "UPDATE ticket SET assigne_a=%s, statut='En_cours' WHERE id_ticket=%s",
            (uid, tid)
        )
        cur.execute("""
            INSERT INTO historique_ticket (id_ticket, ancien_statut, nouveau_statut, change_par, est_systeme, commentaire_log)
            VALUES (%s, %s, 'En_cours', %s, 0, 'Accepté via proposition automatique')
        """, (tid, row['statut'], uid))
        # Annuler d'éventuelles autres propositions en attente sur ce ticket
        cur.execute(
            "UPDATE proposition_ticket SET statut='refusée', date_reponse=NOW() "
            "WHERE id_ticket=%s AND statut='en_attente' AND id_technicien != %s",
            (tid, uid)
        )
        db.commit()
        creer_notification(
            row['cree_par'],
            f"🔧 Votre ticket #{tid} « {row['titre']} » est pris en charge.",
            tid
        )
        flash('Vous avez accepté le ticket. Bonne intervention !', 'success')
    except Exception:
        db.rollback()
        flash("Erreur lors de l'acceptation.", 'danger')
    return redirect(url_for('technicien.detail_ticket', tid=tid))


@bp.route('/ticket/<int:tid>/refuser-proposition', methods=['POST'])
@login_required
@role_required('technicien')
def refuser_proposition(tid):
    db  = database.get_db()
    cur = db.cursor()
    uid = session['user_id']

    cur.execute("""
        SELECT p.id_proposition, t.categorie, t.titre
        FROM proposition_ticket p JOIN ticket t ON t.id_ticket = p.id_ticket
        WHERE p.id_ticket=%s AND p.id_technicien=%s AND p.statut='en_attente'
    """, (tid, uid))
    row = cur.fetchone()
    if not row:
        flash("Cette proposition n'existe plus.", 'warning')
        return redirect(url_for('technicien.dashboard'))

    try:
        cur.execute(
            "UPDATE proposition_ticket SET statut='refusée', date_reponse=NOW() "
            "WHERE id_proposition=%s",
            (row['id_proposition'],)
        )
        db.commit()
    except Exception:
        db.rollback()
        flash("Erreur lors du refus.", 'danger')
        return redirect(url_for('technicien.dashboard'))

    # Proposer au prochain technicien éligible
    try:
        from app.auto_assign import proposer_ticket
        proposer_ticket(db, tid, row['categorie'])
    except Exception:
        pass

    flash('Proposition refusée. Le ticket sera proposé à un autre technicien.', 'info')
    return redirect(url_for('technicien.dashboard'))


# ── ABANDON ──────────────────────────────────────────────────────────────────

@bp.route('/ticket/<int:tid>/abandonner', methods=['POST'])
@login_required
@role_required('technicien')
def abandonner_ticket(tid):
    db  = database.get_db()
    cur = db.cursor()
    uid = session['user_id']
    cur.execute(
        "SELECT * FROM ticket WHERE id_ticket=%s AND assigne_a=%s AND statut='En_cours'",
        (tid, uid)
    )
    ticket = cur.fetchone()
    if not ticket:
        flash('Action impossible.', 'danger')
        return redirect(url_for('technicien.dashboard'))
    try:
        cur.execute(
            "UPDATE ticket SET assigne_a=NULL, statut='En_attente' WHERE id_ticket=%s",
            (tid,)
        )
        cur.execute("""
            INSERT INTO historique_ticket
                (id_ticket, ancien_statut, nouveau_statut, change_par, est_systeme, commentaire_log)
            VALUES (%s, 'En_cours', 'En_attente', %s, 0, 'Technicien désaffecté')
        """, (tid, uid))
        db.commit()
        creer_notification(
            ticket['cree_par'],
            f"⏸ Le technicien s'est désaffecté du ticket #{tid} « {ticket['titre']} ».",
            tid
        )
        # Re-proposer automatiquement
        from app.auto_assign import proposer_ticket
        proposer_ticket(db, tid, ticket['categorie'])
    except Exception:
        db.rollback()
        flash("Erreur lors de la désaffectation.", 'danger')
        return redirect(url_for('technicien.dashboard'))
    flash('Vous vous êtes désaffecté du ticket.', 'info')
    return redirect(url_for('technicien.dashboard'))


# ── RÉSOLUTION ────────────────────────────────────────────────────────────────

@bp.route('/ticket/<int:tid>/resoudre', methods=['POST'])
@login_required
@role_required('technicien')
def resoudre_ticket(tid):
    db  = database.get_db()
    cur = db.cursor()
    uid = session['user_id']
    cur.execute(
        "SELECT * FROM ticket WHERE id_ticket=%s AND assigne_a=%s AND statut='En_cours'",
        (tid, uid)
    )
    ticket = cur.fetchone()
    if not ticket:
        flash('Action impossible.', 'danger')
        return redirect(url_for('technicien.dashboard'))
    try:
        cur.execute("UPDATE ticket SET statut='Résolu' WHERE id_ticket=%s", (tid,))
        cur.execute("""
            INSERT INTO historique_ticket (id_ticket, ancien_statut, nouveau_statut, change_par, est_systeme)
            VALUES (%s, 'En_cours', 'Résolu', %s, 0)
        """, (tid, uid))
        db.commit()
        creer_notification(
            ticket['cree_par'],
            f"✅ Votre ticket #{tid} « {ticket['titre']} » a été résolu. "
            f"Veuillez valider la résolution.",
            tid
        )
        flash('Ticket marqué comme résolu. En attente de validation.', 'success')
    except Exception:
        db.rollback()
        flash("Erreur lors de la résolution.", 'danger')
    return redirect(url_for('technicien.dashboard'))


# ── MODIFICATION STATUT / CATÉGORIE ──────────────────────────────────────────

@bp.route('/ticket/<int:tid>/modifier-statut', methods=['POST'])
@login_required
@role_required('technicien')
def modifier_statut(tid):
    db  = database.get_db()
    cur = db.cursor()
    uid = session['user_id']
    cur.execute(
        "SELECT * FROM ticket WHERE id_ticket=%s AND assigne_a=%s",
        (tid, uid)
    )
    ticket = cur.fetchone()
    if not ticket:
        flash('Action impossible.', 'danger')
        return redirect(url_for('technicien.dashboard'))

    nouveau_statut = request.form.get('statut', '')
    nouvelle_cat   = request.form.get('categorie', '')

    # Valider la transition de statut
    if nouveau_statut:
        statut_actuel = ticket['statut']
        transitions_ok = TRANSITIONS_VALIDES.get(statut_actuel, ())
        if nouveau_statut not in transitions_ok:
            flash(
                f"Transition invalide : impossible de passer de "
                f"« {statut_actuel} » à « {nouveau_statut} ».",
                'danger'
            )
            return redirect(url_for('technicien.detail_ticket', tid=tid))

    try:
        if nouveau_statut:
            cur.execute(
                "UPDATE ticket SET statut=%s WHERE id_ticket=%s",
                (nouveau_statut, tid)
            )
            cur.execute("""
                INSERT INTO historique_ticket
                    (id_ticket, ancien_statut, nouveau_statut, change_par, est_systeme)
                VALUES (%s, %s, %s, %s, 0)
            """, (tid, ticket['statut'], nouveau_statut, uid))
        if nouvelle_cat:
            CATEGORIES_OK = ('Matériel', 'Logiciel', 'Réseau', 'Sécurité', 'Compte/accès')
            if nouvelle_cat in CATEGORIES_OK:
                cur.execute(
                    "UPDATE ticket SET categorie=%s WHERE id_ticket=%s",
                    (nouvelle_cat, tid)
                )
        db.commit()
        flash('Ticket mis à jour.', 'success')
    except Exception:
        db.rollback()
        flash("Erreur lors de la mise à jour.", 'danger')
    return redirect(url_for('technicien.detail_ticket', tid=tid))


# ── COMMENTAIRE ───────────────────────────────────────────────────────────────

@bp.route('/ticket/<int:tid>/commenter', methods=['POST'])
@login_required
@role_required('technicien')
def commenter(tid):
    db  = database.get_db()
    cur = db.cursor()
    uid = session['user_id']
    cur.execute(
        "SELECT * FROM ticket WHERE id_ticket=%s AND assigne_a=%s",
        (tid, uid)
    )
    ticket = cur.fetchone()
    if not ticket:
        flash('Action impossible.', 'danger')
        return redirect(url_for('technicien.dashboard'))
    texte = request.form.get('texte', '').strip()
    if not texte:
        flash('Le commentaire ne peut pas être vide.', 'warning')
        return redirect(url_for('technicien.detail_ticket', tid=tid))
    if len(texte) > 2000:
        flash('Le commentaire est trop long (max. 2000 caractères).', 'warning')
        return redirect(url_for('technicien.detail_ticket', tid=tid))
    try:
        cur.execute(
            "INSERT INTO commentaire (texte, id_ticket, ecrit_par) VALUES (%s, %s, %s)",
            (texte, tid, uid)
        )
        db.commit()
        creer_notification(
            ticket['cree_par'],
            f"💬 Nouveau commentaire sur votre ticket #{tid} « {ticket['titre']} ».",
            tid
        )
        flash('Commentaire ajouté.', 'success')
    except Exception:
        db.rollback()
        flash("Erreur lors de l'ajout du commentaire.", 'danger')
    return redirect(url_for('technicien.detail_ticket', tid=tid))


# ── MES TICKETS ───────────────────────────────────────────────────────────────

@bp.route('/mes-tickets')
@login_required
@role_required('technicien')
def mes_tickets():
    db  = database.get_db()
    cur = db.cursor()
    uid    = session['user_id']
    statut = request.args.get('statut', '')
    query  = """
        SELECT t.*, CONCAT(u.prenom,' ',u.nom) AS utilisateur_nom
        FROM ticket t JOIN utilisateur u ON u.id_utilisateur = t.cree_par
        WHERE t.assigne_a=%s
    """
    params = [uid]
    if statut:
        query += " AND t.statut=%s"
        params.append(statut)
    query += " ORDER BY t.date_creation DESC"
    cur.execute(query, params)
    tickets   = cur.fetchall()
    nb_notifs = count_non_lues(uid)
    return render_template('technicien/mes_tickets.html', tickets=tickets,
                           filtre_statut=statut, nb_notifs=nb_notifs)


# ── NOTIFICATIONS ─────────────────────────────────────────────────────────────

@bp.route('/notifications')
@login_required
@role_required('technicien')
def notifications():
    uid    = session['user_id']
    notifs = get_notifications(uid)
    marquer_lues(uid)
    return render_template('technicien/notifications.html', notifs=notifs, nb_notifs=0)


@bp.route('/notifications/count')
@login_required
@role_required('technicien')
def notif_count():
    return jsonify({'count': count_non_lues(session['user_id'])})


# ── PROFIL ────────────────────────────────────────────────────────────────────

@bp.route('/profil', methods=['GET', 'POST'])
@login_required
@role_required('technicien')
def profil():
    db  = database.get_db()
    cur = db.cursor()
    uid = session['user_id']
    if request.method == 'POST':
        nom       = request.form.get('nom', '').strip()
        prenom    = request.form.get('prenom', '').strip()
        telephone = request.form.get('telephone', '').strip()
        new_mdp   = request.form.get('mot_de_passe', '')
        if not nom or not prenom:
            flash('Nom et prénom obligatoires.', 'danger')
            return redirect(url_for('technicien.profil'))
        try:
            cur.execute(
                "UPDATE utilisateur SET nom=%s, prenom=%s, telephone=%s WHERE id_utilisateur=%s",
                (nom, prenom, telephone, uid)
            )
            if new_mdp:
                if len(new_mdp) < 6:
                    flash('Le mot de passe doit contenir au moins 6 caractères.', 'danger')
                    return redirect(url_for('technicien.profil'))
                from werkzeug.security import generate_password_hash
                cur.execute(
                    "UPDATE utilisateur SET mot_de_passe=%s WHERE id_utilisateur=%s",
                    (generate_password_hash(new_mdp), uid)
                )
            db.commit()
            session['user_nom'] = f"{prenom} {nom}"
            flash('Profil mis à jour.', 'success')
        except Exception:
            db.rollback()
            flash("Erreur lors de la mise à jour.", 'danger')
        return redirect(url_for('technicien.profil'))
    cur.execute("""
        SELECT u.*, t.specialite, t.note_moyenne, t.nb_evaluations
        FROM utilisateur u JOIN technicien t ON t.id_utilisateur = u.id_utilisateur
        WHERE u.id_utilisateur=%s
    """, (uid,))
    user      = cur.fetchone()
    nb_notifs = count_non_lues(uid)
    return render_template('technicien/profil.html', user=user, nb_notifs=nb_notifs)
