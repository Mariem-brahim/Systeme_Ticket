CATEGORIE_SPECIALITE = {
    'Réseau':       'Réseaux',
    'Sécurité':     'Sécurité',
    'Matériel':     'Système',
    'Logiciel':     'Support',
    'Compte/accès': 'Support',
}


def _get_techniciens_eligibles(cur, id_ticket, categorie):
    specialite_cible = CATEGORIE_SPECIALITE.get(categorie)

    # Techniciens ayant déjà refusé ce ticket
    cur.execute(
        "SELECT id_technicien FROM proposition_ticket "
        "WHERE id_ticket = %s AND statut = 'refusée'",
        (id_ticket,)
    )
    deja_refuses = {r['id_technicien'] for r in cur.fetchall()}

    if specialite_cible:
        cur.execute("""
            SELECT t.id_utilisateur, t.note_moyenne,
                   (SELECT COUNT(*) FROM ticket tk
                    WHERE tk.assigne_a = t.id_utilisateur
                      AND tk.statut = 'En_cours') AS charge
            FROM technicien t
            JOIN utilisateur u ON u.id_utilisateur = t.id_utilisateur
            WHERE t.specialite = %s AND u.actif = 1
            ORDER BY t.note_moyenne DESC, charge ASC
        """, (specialite_cible,))
    else:
        cur.execute("""
            SELECT t.id_utilisateur, t.note_moyenne,
                   (SELECT COUNT(*) FROM ticket tk
                    WHERE tk.assigne_a = t.id_utilisateur
                      AND tk.statut = 'En_cours') AS charge
            FROM technicien t
            JOIN utilisateur u ON u.id_utilisateur = t.id_utilisateur
            WHERE u.actif = 1
            ORDER BY t.note_moyenne DESC, charge ASC
        """)

    return [t for t in cur.fetchall() if t['id_utilisateur'] not in deja_refuses]


def proposer_ticket(db, id_ticket, categorie):

    from app.helpers import creer_notification

    cur = db.cursor()

    # Ne pas créer une double proposition active
    cur.execute(
        "SELECT id_proposition FROM proposition_ticket "
        "WHERE id_ticket = %s AND statut = 'en_attente'",
        (id_ticket,)
    )
    if cur.fetchone():
        return True

    cur.execute("SELECT titre FROM ticket WHERE id_ticket = %s", (id_ticket,))
    ticket = cur.fetchone()
    if not ticket:
        return False

    eligibles = _get_techniciens_eligibles(cur, id_ticket, categorie)

    if not eligibles:
        # Escalade vers le directeur
        cur.execute(
            "SELECT id_utilisateur FROM utilisateur "
            "WHERE role = 'directeur' AND actif = 1 LIMIT 1"
        )
        directeur = cur.fetchone()
        if directeur:
            creer_notification(
                directeur['id_utilisateur'],
                f"⚠ Aucun technicien disponible pour le ticket #{id_ticket} "
                f"« {ticket['titre']} ». Intervention manuelle requise.",
                id_ticket
            )
        return False

    tech = eligibles[0]
    try:
        cur.execute(
            "INSERT INTO proposition_ticket (id_ticket, id_technicien) VALUES (%s, %s)",
            (id_ticket, tech['id_utilisateur'])
        )
        db.commit()
        creer_notification(
            tech['id_utilisateur'],
            f"📋 Un ticket vous est proposé automatiquement : "
            f"#{id_ticket} « {ticket['titre']} ».",
            id_ticket
        )
        return True
    except Exception:
        db.rollback()
        return False
