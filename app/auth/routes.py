import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from flask import (render_template, request, redirect, url_for,
                   session, flash, current_app)
from werkzeug.security import check_password_hash
from app.auth import bp
import db as database

OTP_MAX_TENTATIVES = 3


def _generate_otp():
    return str(random.randint(100000, 999999))


def _send_otp(destinataire, code):
    cfg = current_app.config
    msg = MIMEMultipart('alternative')
    msg['Subject'] = 'Votre code de connexion — Autorité de Régulation'
    msg['From']    = cfg['SMTP_USER']
    msg['To']      = destinataire

    texte = f"Votre code de vérification est : {code}\nValable 10 minutes."
    html  = f"""
    <div style="font-family:Arial,sans-serif;max-width:420px;margin:auto;
                padding:2rem;border:1px solid #ddd;border-radius:6px;">
      <h2 style="color:#1a2b4a;">Autorité de Régulation</h2>
      <p>Votre code de connexion :</p>
      <div style="font-size:2.5rem;font-weight:bold;letter-spacing:0.5em;
                  text-align:center;padding:1rem;background:#f5f5f5;
                  border-radius:4px;color:#1a2b4a;">
        {code}
      </div>
      <p style="color:#888;font-size:0.85rem;margin-top:1rem;">
        Ce code expire dans <strong>10 minutes</strong>.<br>
        Si vous n'êtes pas à l'origine de cette demande, ignorez ce message.
      </p>
    </div>
    """
    msg.attach(MIMEText(texte, 'plain', 'utf-8'))
    msg.attach(MIMEText(html,  'html',  'utf-8'))

    with smtplib.SMTP(cfg['SMTP_SERVER'], cfg['SMTP_PORT'], timeout=15) as server:
        server.ehlo()
        server.starttls()
        server.login(cfg['SMTP_USER'], cfg['SMTP_PASSWORD'])
        server.sendmail(cfg['SMTP_USER'], destinataire, msg.as_string())


# ── LOGIN ────────────────────────────────────────────────────────────────────

@bp.route('/', methods=['GET'])
@bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return _redirect_by_role(session.get('role'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        mdp   = request.form.get('mot_de_passe', '')

        db  = database.get_db()
        cur = db.cursor()
        cur.execute(
            "SELECT id_utilisateur, nom, prenom, email, mot_de_passe, role, actif "
            "FROM utilisateur WHERE email = %s",
            (email,)
        )
        user = cur.fetchone()

        if not user or not check_password_hash(user['mot_de_passe'], mdp):
            flash('Email ou mot de passe incorrect.', 'danger')
            return render_template('auth/login.html')

        if not user['actif']:
            flash("Votre compte est désactivé. Contactez l'administrateur.", 'warning')
            return render_template('auth/login.html')

        code   = _generate_otp()
        expire = datetime.now() + timedelta(minutes=10)

        try:
            cur.execute(
                "INSERT INTO verification_email (email, code, expire_le) "
                "VALUES (%s, %s, %s)",
                (email, code, expire)
            )
            db.commit()
        except Exception:
            db.rollback()
            flash("Erreur interne. Veuillez réessayer.", 'danger')
            return render_template('auth/login.html')

        try:
            _send_otp(email, code)
        except Exception as e:
            current_app.logger.error(f"OTP email failed for {email}: {e}")

        flash('Un code de vérification a été envoyé à votre adresse email.', 'info')
        session['pending_user_id'] = user['id_utilisateur']
        session['pending_email']   = email
        return redirect(url_for('auth.verify_otp'))

    return render_template('auth/login.html')

# ── VERIFY OTP ───────────────────────────────────────────────────────────────

@bp.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    if 'pending_user_id' not in session:
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        code  = request.form.get('code', '').strip()
        email = session['pending_email']

        db  = database.get_db()
        cur = db.cursor()

        cur.execute(
            "SELECT id, expire_le, tentatives FROM verification_email "
            "WHERE email = %s AND code = %s AND utilise = 0 "
            "ORDER BY created_at DESC LIMIT 1",
            (email, code)
        )
        record = cur.fetchone()

        if not record:
            cur.execute(
                "UPDATE verification_email SET tentatives = tentatives + 1 "
                "WHERE email = %s AND utilise = 0 ORDER BY created_at DESC LIMIT 1",
                (email,)
            )
            db.commit()

            cur.execute(
                "SELECT tentatives FROM verification_email "
                "WHERE email = %s AND utilise = 0 ORDER BY created_at DESC LIMIT 1",
                (email,)
            )
            t = cur.fetchone()
            tentatives = t['tentatives'] if t else OTP_MAX_TENTATIVES

            if tentatives >= OTP_MAX_TENTATIVES:
                cur.execute(
                    "UPDATE verification_email SET utilise = 1 "
                    "WHERE email = %s AND utilise = 0",
                    (email,)
                )
                db.commit()
                session.clear()
                flash('Trop de tentatives. Veuillez vous reconnecter.', 'danger')
                return redirect(url_for('auth.login'))

            restantes = OTP_MAX_TENTATIVES - tentatives
            flash(f'Code incorrect. {restantes} tentative(s) restante(s).', 'danger')
            return render_template('auth/verify_otp.html')

        if record['expire_le'] < datetime.now():
            flash('Code expiré. Veuillez vous reconnecter.', 'warning')
            session.clear()
            return redirect(url_for('auth.login'))

        # OTP valide
        try:
            cur.execute(
                "UPDATE verification_email SET utilise = 1 WHERE id = %s",
                (record['id'],)
            )
            db.commit()
        except Exception:
            db.rollback()
            flash("Erreur interne. Veuillez réessayer.", 'danger')
            return render_template('auth/verify_otp.html')

        cur.execute(
            "SELECT id_utilisateur, nom, prenom, email, role "
            "FROM utilisateur WHERE id_utilisateur = %s",
            (session['pending_user_id'],)
        )
        user = cur.fetchone()
        session.clear()
        session['user_id']    = user['id_utilisateur']
        session['user_nom']   = f"{user['prenom']} {user['nom']}"
        session['user_email'] = user['email']
        session['role']       = user['role']
        session.permanent     = True

        return _redirect_by_role(user['role'])

    return render_template('auth/verify_otp.html')


# ── LOGOUT ───────────────────────────────────────────────────────────────────

@bp.route('/logout')
def logout():
    session.clear()
    flash('Vous avez été déconnecté.', 'info')
    return redirect(url_for('auth.login'))


def _redirect_by_role(role):
    mapping = {
        'utilisateur':    'utilisateur.dashboard',
        'technicien':     'technicien.dashboard',
        'directeur':      'directeur.dashboard',
        'administrateur': 'admin.dashboard',
    }
    return redirect(url_for(mapping.get(role, 'auth.login')))
