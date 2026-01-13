from flask import render_template, send_file, request, session, redirect, url_for, flash, jsonify
from werkzeug.security import generate_password_hash
from app.directeur import bp
from app.decorators import login_required, role_required
from app.helpers import ( count_non_lues, get_notifications,
                          marquer_lues, generer_rapport_pdf)
import db as database
from datetime import datetime


def _get_stats(cur, annee=None, mois=None):
    """Retourne les statistiques, filtrées par mois/année si fournis."""
    has_filter   = bool(annee and mois)
    filtre_sql   = "WHERE YEAR(date_creation)=%s AND MONTH(date_creation)=%s" if has_filter else ""
    filtre_param = [annee, mois] if has_filter else []

    cur.execute(
        f"SELECT statut, COUNT(*) as nb FROM ticket {filtre_sql} GROUP BY statut",
        filtre_param
    )
    stats_statut = {r['statut']: r['nb'] for r in cur.fetchall()}

    cur.execute(
        f"SELECT priorite, COUNT(*) as nb FROM ticket {filtre_sql} GROUP BY priorite",
        filtre_param
    )
    stats_priorite = {r['priorite']: r['nb'] for r in cur.fetchall()}

    cur.execute(
        f"SELECT categorie, COUNT(*) as nb FROM ticket {filtre_sql} GROUP BY categorie",
        filtre_param
    )
    stats_categorie = {r['categorie']: r['nb'] for r in cur.fetchall()}

    cur.execute(f"SELECT COUNT(*) as total FROM ticket {filtre_sql}", filtre_param)
    total = cur.fetchone()['total']

    # Temps moyen de résolution (heures)
    filtre_res = ("AND YEAR(date_creation)=%s AND MONTH(date_creation)=%s"
                  if has_filter else "")
    cur.execute(
        f"SELECT AVG(TIMESTAMPDIFF(HOUR, date_creation, date_resolution)) AS tps_moyen "
        f"FROM ticket WHERE date_resolution IS NOT NULL {filtre_res}",
        filtre_param
    )
    row = cur.fetchone()
    tps_moyen = round(float(row['tps_moyen']), 1) if row and row['tps_moyen'] else None

    # Top techniciens
    filtre_tech       = "AND YEAR(tk.date_creation)=%s AND MONTH(tk.date_creation)=%s" if has_filter else ""
    filtre_tech_param = [annee, mois] if has_filter else []

    cur.execute(f"""
        SELECT u.prenom, u.nom, t.specialite, t.note_moyenne, t.nb_evaluations,
               COUNT(tk.id_ticket) AS nb_resolus
        FROM technicien t
        JOIN utilisateur u ON u.id_utilisateur = t.id_utilisateur
        LEFT JOIN ticket tk ON tk.assigne_a = t.id_utilisateur
            AND tk.statut = 'Clôturé' {filtre_tech}
        GROUP BY t.id_utilisateur
        ORDER BY t.note_moyenne DESC
        LIMIT 3
    """, filtre_tech_param)
    top_tech = cur.fetchall()

    # Évolution sur 6 mois (pas filtrée — toujours la fenêtre glissante)
    cur.execute("""
        SELECT DATE_FORMAT(date_creation,'%Y-%m') as mois, COUNT(*) as nb
        FROM ticket
        WHERE date_creation >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
        GROUP BY mois ORDER BY mois ASC
    """)
    evolution = cur.fetchall()

    # Derniers tickets
    filtre_recent = ("WHERE YEAR(t.date_creation)=%s AND MONTH(t.date_creation)=%s"
                     if has_filter else "")
    cur.execute(f"""
        SELECT t.*, CONCAT(u.prenom,' ',u.nom) AS createur
        FROM ticket t JOIN utilisateur u ON u.id_utilisateur = t.cree_par
        {filtre_recent}
        ORDER BY t.date_creation DESC LIMIT 10
    """, filtre_param)
    recents = cur.fetchall()

    return (stats_statut, stats_priorite, stats_categorie,
            total, tps_moyen, top_tech, evolution, recents)


@bp.route('/dashboard')
@login_required
@role_required('directeur')
def dashboard():
    periode = request.args.get('periode', '')
    annee, mois, mois_label = None, None, "Toutes périodes"
    if periode:
        try:
            dt = datetime.strptime(periode, '%Y-%m')
            annee, mois = dt.year, dt.month
            mois_label  = dt.strftime('%B %Y')
        except ValueError:
            periode = ''

    db  = database.get_db()
    cur = db.cursor()
    stats_statut, stats_priorite, stats_categorie, total, tps_moyen, \
        top_tech, evolution, recents = _get_stats(cur, annee, mois)

    cur.execute("""
        SELECT DISTINCT DATE_FORMAT(date_creation,'%Y-%m') AS m
        FROM ticket ORDER BY m DESC LIMIT 24
    """)
    periodes_dispo = [r['m'] for r in cur.fetchall()]
    nb_notifs      = count_non_lues(session['user_id'])

    return render_template('directeur/dashboard.html',
                           stats_statut=stats_statut,
                           stats_priorite=stats_priorite,
                           stats_categorie=stats_categorie,
                           total=total, tps_moyen=tps_moyen,
                           top_tech=top_tech,
                           evolution=evolution, recents=recents,
                           periode=periode, mois_label=mois_label,
                           periodes_dispo=periodes_dispo,
                           nb_notifs=nb_notifs)


@bp.route('/rapport-pdf')
@login_required
@role_required('directeur')
def rapport_pdf():
    periode = request.args.get('periode', '')
    annee, mois, mois_label = None, None, datetime.now().strftime('%B %Y')
    if periode:
        try:
            dt = datetime.strptime(periode, '%Y-%m')
            annee, mois = dt.year, dt.month
            mois_label  = dt.strftime('%B %Y')
        except ValueError:
            pass

    db  = database.get_db()
    cur = db.cursor()
    stats_statut, stats_priorite, stats_categorie, total, tps_moyen, \
        top_tech, evolution, _ = _get_stats(cur, annee, mois)

    buffer   = generer_rapport_pdf(stats_statut, stats_priorite, stats_categorie,
                                    top_tech, evolution, total, mois_label, tps_moyen)
    suffix   = f"_{periode}" if periode else ""
    filename = f"rapport_tickets{suffix}.pdf"
    return send_file(buffer, mimetype='application/pdf',
                     as_attachment=True, download_name=filename)


@bp.route('/rapport-apercu')
@login_required
@role_required('directeur')
def rapport_apercu():
    """Page d'aperçu HTML du rapport avant téléchargement PDF."""
    periode = request.args.get('periode', '')
    annee, mois, mois_label = None, None, "Toutes périodes"
    if periode:
        try:
            dt = datetime.strptime(periode, '%Y-%m')
            annee, mois = dt.year, dt.month
            mois_label  = dt.strftime('%B %Y')
        except ValueError:
            periode = ''

    db  = database.get_db()
    cur = db.cursor()
    stats_statut, stats_priorite, stats_categorie, total, tps_moyen, \
        top_tech, evolution, _ = _get_stats(cur, annee, mois)

    resolus = stats_statut.get('Clôturé', 0) + stats_statut.get('Résolu', 0)
    taux    = round(resolus / total * 100, 1) if total > 0 else 0
    nb_notifs = count_non_lues(session['user_id'])

    return render_template('directeur/rapport_apercu.html',
                           stats_statut=stats_statut,
                           stats_priorite=stats_priorite,
                           stats_categorie=stats_categorie,
                           top_tech=top_tech,
                           total=total, taux=taux,
                           tps_moyen=tps_moyen,
                           mois_label=mois_label,
                           periode=periode,
                           nb_notifs=nb_notifs)


@bp.route('/notifications')
@login_required
@role_required('directeur')
def notifications():
    uid    = session['user_id']
    notifs = get_notifications(uid)
    marquer_lues(uid)
    return render_template('directeur/notifications.html', notifs=notifs, nb_notifs=0)


@bp.route('/notifications/count')
@login_required
@role_required('directeur')
def notif_count():
    return jsonify({'count': count_non_lues(session['user_id'])})


@bp.route('/profil', methods=['GET', 'POST'])
@login_required
@role_required('directeur')
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
            return redirect(url_for('directeur.profil'))
        try:
            cur.execute(
                "UPDATE utilisateur SET nom=%s, prenom=%s, telephone=%s WHERE id_utilisateur=%s",
                (nom, prenom, telephone, uid)
            )
            if new_mdp:
                if len(new_mdp) < 6:
                    flash('Le mot de passe doit contenir au moins 6 caractères.', 'danger')
                    return redirect(url_for('directeur.profil'))
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
        return redirect(url_for('directeur.profil'))

    cur.execute("SELECT * FROM utilisateur WHERE id_utilisateur=%s", (uid,))
    user      = cur.fetchone()
    nb_notifs = count_non_lues(uid)
    return render_template('directeur/profil.html', user=user, nb_notifs=nb_notifs)
