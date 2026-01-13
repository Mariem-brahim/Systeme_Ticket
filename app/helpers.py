"""
Utilitaires partagés : notifications et génération de rapports PDF.
"""
import io
import os
from datetime import datetime
import db as database


# ── NOTIFICATIONS ─────────────────────────────────────────────────────────────

def creer_notification(id_utilisateur, message, id_ticket=None):
    try:
        db  = database.get_db()
        cur = db.cursor()
        cur.execute(
            "INSERT INTO notification (id_utilisateur, message, id_ticket) "
            "VALUES (%s, %s, %s)",
            (id_utilisateur, message, id_ticket)
        )
        db.commit()
    except Exception as e:
        print(f"[NOTIF ERROR] {e}")


def get_notifications(id_utilisateur, non_lues_seulement=False):
    db  = database.get_db()
    cur = db.cursor()
    if non_lues_seulement:
        cur.execute(
            "SELECT * FROM notification WHERE id_utilisateur=%s AND lu=0 "
            "ORDER BY created_at DESC",
            (id_utilisateur,)
        )
    else:
        cur.execute(
            "SELECT * FROM notification WHERE id_utilisateur=%s "
            "ORDER BY created_at DESC LIMIT 50",
            (id_utilisateur,)
        )
    return cur.fetchall()


def count_non_lues(id_utilisateur):
    db  = database.get_db()
    cur = db.cursor()
    cur.execute(
        "SELECT COUNT(*) as nb FROM notification "
        "WHERE id_utilisateur=%s AND lu=0",
        (id_utilisateur,)
    )
    return cur.fetchone()['nb']


def marquer_lues(id_utilisateur):
    db  = database.get_db()
    cur = db.cursor()
    cur.execute(
        "UPDATE notification SET lu=1 WHERE id_utilisateur=%s AND lu=0",
        (id_utilisateur,)
    )
    db.commit()


# ── RAPPORT PDF ───────────────────────────────────────────────────────────────

def generer_rapport_pdf(stats_statut, stats_priorite, stats_categorie,
                         top_tech, evolution, total, mois_label, tps_moyen=None):
    import arabic_reshaper
    from bidi.algorithm import get_display
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                     Table, TableStyle, HRFlowable, Image)
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

    # Register Tahoma (Arabic-capable) — safe to call multiple times
    FONTS = r'C:\Windows\Fonts'
    try:
        pdfmetrics.registerFont(TTFont('Tahoma',     os.path.join(FONTS, 'tahoma.ttf')))
        pdfmetrics.registerFont(TTFont('TahomaBold', os.path.join(FONTS, 'tahomabd.ttf')))
    except Exception:
        pass  # already registered

    def ar(text):
        """Reshape + bidi-reorder Arabic text for LTR rendering engines."""
        return get_display(arabic_reshaper.reshape(text))

    buffer   = io.BytesIO()
    USABLE_W = A4[0] - 4 * cm
    doc      = SimpleDocTemplate(buffer, pagesize=A4,
                                  rightMargin=2*cm, leftMargin=2*cm,
                                  topMargin=1.5*cm, bottomMargin=2*cm)

    styles = getSampleStyleSheet()
    NAVY      = colors.HexColor('#1a2b4a')
    GOLD      = colors.HexColor('#c9a84c')
    DARK_BLUE = colors.HexColor('#003580')
    LIGHT     = colors.HexColor('#f0f0f0')
    WHITE     = colors.white

    # ── Paragraph styles ──────────────────────────────────────────────────────
    s_section = ParagraphStyle('section', parent=styles['Normal'],
                                fontSize=12, textColor=NAVY,
                                fontName='Helvetica-Bold', spaceBefore=14, spaceAfter=5)
    s_normal  = ParagraphStyle('normal',  parent=styles['Normal'], fontSize=10, leading=14)
    s_recomm  = ParagraphStyle('recomm',  parent=styles['Normal'],
                                fontSize=10, leading=16, leftIndent=12)
    s_footer  = ParagraphStyle('footer',  parent=styles['Normal'], fontSize=8,
                                textColor=colors.HexColor('#999999'), alignment=TA_CENTER)

    # Letterhead — French (left column)
    s_fr1 = ParagraphStyle('fr1', parent=styles['Normal'],
                            fontName='Helvetica-Bold', fontSize=8, leading=11,
                            alignment=TA_LEFT)
    s_fr2 = ParagraphStyle('fr2', parent=styles['Normal'],
                            fontName='Helvetica-Oblique', fontSize=7, leading=10,
                            textColor=colors.HexColor('#444444'), alignment=TA_LEFT)
    s_fr3 = ParagraphStyle('fr3', parent=styles['Normal'],
                            fontName='Helvetica-Bold', fontSize=10, leading=13,
                            spaceBefore=5, alignment=TA_LEFT)
    s_fr4 = ParagraphStyle('fr4', parent=styles['Normal'],
                            fontName='Helvetica-Bold', fontSize=8, leading=11,
                            alignment=TA_LEFT)

    # Letterhead — Arabic (right column, right-aligned)
    s_ar1 = ParagraphStyle('ar1', parent=styles['Normal'],
                            fontName='TahomaBold', fontSize=9, leading=13,
                            alignment=TA_RIGHT)
    s_ar2 = ParagraphStyle('ar2', parent=styles['Normal'],
                            fontName='Tahoma', fontSize=8, leading=11,
                            textColor=colors.HexColor('#444444'), alignment=TA_RIGHT)
    s_ar3 = ParagraphStyle('ar3', parent=styles['Normal'],
                            fontName='TahomaBold', fontSize=11, leading=14,
                            spaceBefore=5, alignment=TA_RIGHT)
    s_ar4 = ParagraphStyle('ar4', parent=styles['Normal'],
                            fontName='TahomaBold', fontSize=8, leading=11,
                            alignment=TA_RIGHT)

    # Report title below letterhead
    s_rpt_title = ParagraphStyle('rpt_title', parent=styles['Normal'],
                                  fontName='Helvetica-Bold', fontSize=13,
                                  textColor=NAVY, alignment=TA_CENTER,
                                  spaceBefore=6, spaceAfter=6)
    s_rpt_sub   = ParagraphStyle('rpt_sub', parent=styles['Normal'],
                                  fontSize=9, textColor=colors.HexColor('#666666'),
                                  alignment=TA_CENTER, spaceBefore=4, spaceAfter=4)

    # Table cell styles
    s_th   = ParagraphStyle('th',   parent=styles['Normal'], fontSize=10, leading=13,
                             fontName='Helvetica-Bold', textColor=WHITE,
                             alignment=TA_CENTER)
    s_th_l = ParagraphStyle('th_l', parent=styles['Normal'], fontSize=10, leading=13,
                             fontName='Helvetica-Bold', textColor=WHITE)
    s_td   = ParagraphStyle('td',   parent=styles['Normal'], fontSize=10, leading=13)
    s_tdc  = ParagraphStyle('tdc',  parent=styles['Normal'], fontSize=10, leading=13,
                             alignment=TA_CENTER)
    s_tdb  = ParagraphStyle('tdb',  parent=styles['Normal'], fontSize=10, leading=13,
                             fontName='Helvetica-Bold')

    # ── Base table style factory ───────────────────────────────────────────────
    def tbl_style(gold_last=False):
        cmds = [
            ('BACKGROUND',    (0, 0), (-1, 0),  NAVY),
            ('ROWBACKGROUNDS',(0, 1), (-1, -1), [LIGHT, WHITE]),
            ('GRID',          (0, 0), (-1, -1), 0.4, colors.HexColor('#cccccc')),
            ('TOPPADDING',    (0, 0), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
            ('LEFTPADDING',   (0, 0), (-1, -1), 8),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 8),
            ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ]
        if gold_last:
            cmds += [('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e8e0cc'))]
        return TableStyle(cmds)

    el = []

    # ── En-tête officiel (letterhead) ─────────────────────────────────────────
    logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              'static', 'img', 'logo1.png')

    # French column
    fr_col = [
        Paragraph("REPUBLIQUE ISLAMIQUE DE MAURITANIE", s_fr1),
        Paragraph("Honneur – Fraternité – Justice", s_fr2),
        Paragraph("AUTORITE DE REGULATION", s_fr3),
        Paragraph("CONSEIL NATIONAL DE REGULATION", s_fr4),
    ]

    # Arabic column (reshaped + bidi for correct display)
    ar_col = [
        Paragraph(ar("الجمهورية الإسلامية الموريتانية"), s_ar1),
        Paragraph(ar("شرف – إخاء – عدالة"), s_ar2),
        Paragraph(ar("سلطة التنظيم"), s_ar3),
        Paragraph(ar("المجلس الوطني للتنظيم"), s_ar4),
    ]

    # Logo centre cell
    LW = USABLE_W * 0.22
    if os.path.exists(logo_path):
        logo_cell = Image(logo_path, width=LW * 0.85, height=LW * 0.85)
    else:
        logo_cell = Paragraph("AR", ParagraphStyle('lp', parent=styles['Normal'],
                               fontSize=18, fontName='Helvetica-Bold',
                               alignment=TA_CENTER, textColor=NAVY))

    col_fr = USABLE_W * 0.39
    col_lo = USABLE_W * 0.22
    col_ar = USABLE_W - col_fr - col_lo

    hdr_tbl = Table([[fr_col, logo_cell, ar_col]],
                    colWidths=[col_fr, col_lo, col_ar])
    hdr_tbl.setStyle(TableStyle([
        ('VALIGN',        (0, 0), (-1, 0), 'MIDDLE'),
        ('ALIGN',         (1, 0), (1, 0),  'CENTER'),
        ('TOPPADDING',    (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('LEFTPADDING',   (0, 0), (0, 0),  0),
        ('RIGHTPADDING',  (2, 0), (2, 0),  0),
    ]))
    el.append(hdr_tbl)

    # Decorative double line (blue + gold) — matches official letterhead
    el.append(HRFlowable(width='100%', thickness=2.5, color=DARK_BLUE, spaceAfter=1))
    el.append(HRFlowable(width='100%', thickness=1,   color=GOLD,      spaceAfter=8))

    # Report title + period
    el.append(Paragraph("Rapport — Système de Suivi des Tickets", s_rpt_title))
    el.append(Paragraph(f"Période : {mois_label}", s_rpt_sub))
    el.append(HRFlowable(width='100%', thickness=0.5,
                          color=colors.HexColor('#cccccc'), spaceAfter=10))

    # ── 1. Résumé exécutif ────────────────────────────────────────────────────
    el.append(Paragraph("1. Résumé exécutif", s_section))
    resolus   = stats_statut.get('Clôturé', 0) + stats_statut.get('Résolu', 0)
    taux      = round(resolus / total * 100, 1) if total > 0 else 0
    en_cours  = stats_statut.get('En_cours', 0)
    en_att    = stats_statut.get('En_attente', 0)
    reouverts = stats_statut.get('Réouvert', 0)

    parts = [
        f"Période <b>{mois_label}</b> — <b>{total} tickets</b> enregistrés.",
        f"Taux de résolution : <b>{taux}%</b> ({resolus} clôturés).",
    ]
    if en_cours:  parts.append(f"{en_cours} ticket(s) en cours.")
    if en_att:    parts.append(f"{en_att} ticket(s) en attente.")
    if reouverts: parts.append(f"{reouverts} ticket(s) réouvert(s).")
    if tps_moyen is not None:
        parts.append(f"Temps moyen de traitement : <b>{tps_moyen}h</b>.")
    el.append(Paragraph(" ".join(parts), s_normal))
    el.append(Spacer(1, 0.3*cm))

    # ── 2. Statistiques par statut ────────────────────────────────────────────
    el.append(Paragraph("2. Statistiques par statut", s_section))
    cw2 = [USABLE_W * 0.47, USABLE_W * 0.24, USABLE_W * 0.29]
    rows2 = [[Paragraph('Statut', s_th_l),
              Paragraph('Nombre', s_th),
              Paragraph('Pourcentage', s_th)]]
    for statut, nb in stats_statut.items():
        pct = f"{round(nb / total * 100, 1)}%" if total > 0 else "0%"
        rows2.append([Paragraph(statut, s_td),
                      Paragraph(str(nb), s_tdc),
                      Paragraph(pct, s_tdc)])
    rows2.append([Paragraph('TOTAL', s_tdb),
                  Paragraph(str(total), s_tdb),
                  Paragraph('100%', s_tdb)])
    t2 = Table(rows2, colWidths=cw2, repeatRows=1)
    t2.setStyle(tbl_style(gold_last=True))
    el.append(t2)
    el.append(Spacer(1, 0.3*cm))

    # ── 3. Répartition par priorité ───────────────────────────────────────────
    el.append(Paragraph("3. Répartition par priorité", s_section))
    cw3 = [USABLE_W * 0.6, USABLE_W * 0.4]
    rows3 = [[Paragraph('Priorité', s_th_l), Paragraph('Nombre', s_th)]]
    for p, nb in stats_priorite.items():
        rows3.append([Paragraph(p, s_td), Paragraph(str(nb), s_tdc)])
    t3 = Table(rows3, colWidths=cw3, repeatRows=1)
    t3.setStyle(tbl_style())
    el.append(t3)
    el.append(Spacer(1, 0.3*cm))

    # ── 4. Répartition par catégorie ──────────────────────────────────────────
    el.append(Paragraph("4. Répartition par catégorie", s_section))
    rows4 = [[Paragraph('Catégorie', s_th_l), Paragraph('Nombre', s_th)]]
    for c, nb in stats_categorie.items():
        rows4.append([Paragraph(c, s_td), Paragraph(str(nb), s_tdc)])
    t4 = Table(rows4, colWidths=cw3, repeatRows=1)
    t4.setStyle(tbl_style())
    el.append(t4)
    el.append(Spacer(1, 0.3*cm))

    # ── 5. Performance des techniciens ────────────────────────────────────────
    el.append(Paragraph("5. Performance des techniciens", s_section))
    if top_tech:
        meilleur = top_tech[0]
        note_m   = (round(float(meilleur['note_moyenne']), 2)
                    if meilleur['nb_evaluations'] else 'N/A')
        el.append(Paragraph(
            f"<b>Meilleur technicien :</b> {meilleur['prenom']} {meilleur['nom']} "
            f"(Note : {note_m}/5 — {meilleur['nb_resolus']} tickets clôturés)",
            s_normal
        ))
        el.append(Spacer(1, 0.3*cm))
        cw5 = [USABLE_W * 0.30, USABLE_W * 0.25,
               USABLE_W * 0.15, USABLE_W * 0.15, USABLE_W * 0.15]
        rows5 = [[Paragraph('Technicien', s_th_l),
                  Paragraph('Spécialité', s_th_l),
                  Paragraph('Note /5', s_th),
                  Paragraph('Évals', s_th),
                  Paragraph('Clôturés', s_th)]]
        for t_ in top_tech:
            note = (f"{round(float(t_['note_moyenne']), 2)}"
                    if t_['nb_evaluations'] > 0 else '—')
            rows5.append([
                Paragraph(f"{t_['prenom']} {t_['nom']}", s_td),
                Paragraph(str(t_['specialite']), s_td),
                Paragraph(note, s_tdc),
                Paragraph(str(t_['nb_evaluations']), s_tdc),
                Paragraph(str(t_['nb_resolus']), s_tdc),
            ])
        t5 = Table(rows5, colWidths=cw5, repeatRows=1)
        t5.setStyle(tbl_style())
        el.append(t5)
    else:
        el.append(Paragraph("Aucun technicien enregistré.", s_normal))

    # ── 6. Recommandations ────────────────────────────────────────────────────
    el.append(Paragraph("6. Recommandations", s_section))
    recomms = []
    if taux < 70:
        recomms.append("• Taux de résolution inférieur à 70 % — renforcer l'équipe technique.")
    if stats_priorite.get('Haute', 0) > total * 0.4:
        recomms.append("• Forte proportion de tickets haute priorité — revoir la politique de priorisation.")
    if reouverts > 0:
        recomms.append(f"• {reouverts} ticket(s) réouvert(s) — améliorer la qualité des résolutions.")
    if en_att > total * 0.2:
        recomms.append("• Nombre élevé de tickets en attente — identifier les blocages.")
    if tps_moyen and tps_moyen > 48:
        recomms.append(f"• Temps moyen de traitement élevé ({tps_moyen}h) — optimiser la résolution.")
    if not recomms:
        recomms.append("• Performances satisfaisantes. Maintenir le niveau de service actuel.")
    for r in recomms:
        el.append(Paragraph(r, s_recomm))

    # ── Pied de page — dessiné directement sur le canvas, ancré en bas ────────
    _year = datetime.now().year

    def _draw_footer(canvas, doc):
        canvas.saveState()
        x1 = doc.leftMargin
        x2 = doc.leftMargin + doc.width
        y  = doc.bottomMargin - 0.5 * cm
        canvas.setStrokeColor(GOLD)
        canvas.setLineWidth(1)
        canvas.line(x1, y + 0.35 * cm, x2, y + 0.35 * cm)
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#999999'))
        canvas.drawCentredString(
            (x1 + x2) / 2, y,
            f"Document confidentiel — Autorité de Régulation — {_year}"
        )
        canvas.restoreState()

    doc.build(el, onFirstPage=_draw_footer, onLaterPages=_draw_footer)
    buffer.seek(0)
    return buffer