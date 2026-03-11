"""
Generador de PDF formato R-05-01 para Metalúrgica Ceibo S.R.L.
Genera PDFs idénticos al registro oficial de NC y PNC.

Uso:
    from apps.core.pdf_generator import generate_nc_pdf, generate_pnc_pdf
    buffer = generate_nc_pdf(nc_instance)
    buffer = generate_pnc_pdf(pnc_instance)
"""
import os
from io import BytesIO

from django.conf import settings

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfgen import canvas


# ============================================================
# CONFIGURACIÓN
# ============================================================
PAGE_W, PAGE_H = A4  # 595.28 x 841.89 pts

MARGIN_L = 12 * mm
MARGIN_R = 12 * mm
MARGIN_T = 10 * mm
MARGIN_B = 10 * mm

SIDEBAR_W = 22 * mm  # Columna lateral con textos verticales
CONTENT_L = MARGIN_L + SIDEBAR_W
CONTENT_W = PAGE_W - CONTENT_L - MARGIN_R

# Colores de las franjas laterales
COLOR_SECTOR = colors.HexColor("#e8e8e8")
COLOR_ORG = colors.HexColor("#d8d8d8")
COLOR_AUDITOR = colors.HexColor("#e8e8e8")
COLOR_SISTEMAS = colors.HexColor("#d8d8d8")

FONT = "Helvetica"
FONT_B = "Helvetica-Bold"


# ============================================================
# HELPERS
# ============================================================
def _get_logo_path():
    paths = [
        os.path.join(settings.BASE_DIR, "static", "img", "logo_ceibo.jpeg"),
        os.path.join(settings.STATIC_ROOT or "", "img", "logo_ceibo.jpeg"),
    ]
    for p in paths:
        if os.path.exists(p):
            return p
    return None


def _fmt_date(d):
    if not d:
        return ""
    if isinstance(d, str):
        return d
    return d.strftime("%d/%m/%Y")


def _safe(value, default="-"):
    if value is None or str(value).strip() == "":
        return default
    return str(value)


def _user_name(user):
    if not user:
        return "-"
    name = f"{user.first_name} {user.last_name}".strip()
    return name or user.username


def _draw_checkbox(c, x, y, checked=False, size=8):
    """Dibuja un checkbox cuadrado con X si checked."""
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.5)
    c.rect(x, y, size, size)
    if checked:
        c.setLineWidth(1)
        c.line(x + 1.5, y + 1.5, x + size - 1.5, y + size - 1.5)
        c.line(x + 1.5, y + size - 1.5, x + size - 1.5, y + 1.5)
        c.setLineWidth(0.5)


def _draw_vertical_text(c, x, y_bottom, y_top, text, bg_color):
    """Dibuja texto vertical rotado 90° en la franja lateral, en 2 líneas si es necesario."""
    height = y_top - y_bottom

    # Fondo
    c.setFillColor(bg_color)
    c.rect(MARGIN_L, y_bottom, SIDEBAR_W, height, fill=1, stroke=1)
    c.setFillColor(colors.black)

    # Partir texto en 2 líneas: "A ser completado" + "por el/la XXXX"
    parts = text.split(" por ", 1)
    if len(parts) == 2:
        line1 = "A ser completado"
        line2 = "por " + parts[1]
    else:
        line1 = text
        line2 = ""

    mid_y = (y_top + y_bottom) / 2
    font_size = 7

    c.saveState()
    c.translate(MARGIN_L + SIDEBAR_W / 2, mid_y)
    c.rotate(90)
    c.setFont(FONT_B, font_size)

    if line2:
        c.drawCentredString(0, 2, line1)
        c.drawCentredString(0, -7, line2)
    else:
        c.drawCentredString(0, 0, line1)

    c.restoreState()


def _draw_multiline(c, x, y, text, max_width, font=FONT, size=8, leading=10, max_lines=12):
    """Dibuja texto multilínea respetando max_width."""
    text = _safe(text, "")
    if not text or text == "-":
        return y

    t = c.beginText(x, y)
    t.setFont(font, size)
    t.setLeading(leading)

    for line in text.split("\n")[:max_lines]:
        # Truncar líneas muy largas
        while len(line) > 0:
            # Estimar chars por ancho
            chars = int(max_width / (size * 0.5))
            if len(line) <= chars:
                t.textLine(line)
                break
            # Buscar espacio para cortar
            cut = line[:chars].rfind(" ")
            if cut <= 0:
                cut = chars
            t.textLine(line[:cut])
            line = line[cut:].lstrip()

    c.drawText(t)
    return t.getY()


# ============================================================
# HEADER (común para NC y PNC)
# ============================================================
def _draw_header(c, title, code_label):
    """Dibuja el header con logo, título y fecha."""
    y_top = PAGE_H - MARGIN_T
    h = 18 * mm
    y_bot = y_top - h

    # Caja completa del header
    c.setStrokeColor(colors.black)
    c.setLineWidth(1)
    c.rect(MARGIN_L, y_bot, PAGE_W - MARGIN_L - MARGIN_R, h)

    # Columnas del header
    col2_x = MARGIN_L + 38 * mm
    col3_x = PAGE_W - MARGIN_R - 58 * mm
    c.setLineWidth(0.5)
    c.line(col2_x, y_bot, col2_x, y_top)
    c.line(col3_x, y_bot, col3_x, y_top)

    # Logo
    logo = _get_logo_path()
    if logo:
        try:
            c.drawImage(logo, MARGIN_L + 2 * mm, y_bot + 2 * mm,
                        width=34 * mm, height=14 * mm,
                        preserveAspectRatio=True, mask="auto")
        except Exception:
            c.setFont(FONT_B, 14)
            c.drawString(MARGIN_L + 5 * mm, y_bot + 7 * mm, "CEIBO")

    # Centro
    c.setFont(FONT_B, 9)
    c.drawString(col2_x + 3 * mm, y_top - 6 * mm, title)
    c.setFont(FONT, 7)
    c.drawString(col2_x + 3 * mm, y_top - 11 * mm, f"Código: {code_label}")
    c.drawString(col2_x + 3 * mm, y_top - 15 * mm, "Versión: REV.00")

    # Derecha
    c.setFont(FONT, 7)
    c.drawString(col3_x + 3 * mm, y_top - 6 * mm, "Fecha Aprobación: 29/04/2024")
    c.drawString(col3_x + 3 * mm, y_top - 11 * mm, "Página 1 de 1")

    return y_bot


# ============================================================
# GENERADOR NC
# ============================================================
def generate_nc_pdf(nc):
    """Genera PDF formato R-05-01 para una No Conformidad."""
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    c.setTitle(f"R-05-01_{nc.code}")

    # Header
    y = _draw_header(c, "Registro de No Conformidades", "R-05-01")

    # Título
    y -= 8 * mm
    c.setFont(FONT_B, 12)
    c.drawCentredString(PAGE_W / 2, y, "Reporte de No Conformidad")
    y -= 6 * mm

    content_start_y = y

    fixed_h = (5 + 6.5 + 5 + 5 + 5 + 5 + 6.5 + 10) * mm
    flex_base = {
        "desc_h": 28 * mm,
        "rca_h": 25 * mm,
        "ca_h": 25 * mm,
        "comments_h": 22 * mm,
        "sys_h": 40 * mm,
    }
    available_h = content_start_y - MARGIN_B
    flex_base_total = sum(flex_base.values())
    scale = 1.0
    if flex_base_total > 0 and available_h > fixed_h:
        scale = max((available_h - fixed_h) / flex_base_total, 1.0)

    desc_h = flex_base["desc_h"] * scale
    rca_h = flex_base["rca_h"] * scale
    ca_h = flex_base["ca_h"] * scale
    comments_h = flex_base["comments_h"] * scale
    sys_h = flex_base["sys_h"] * scale

    # Tracking de posiciones para franjas laterales
    sections = {}

    # ========================================
    # SECCIÓN 1: Responsable de Sector
    # ========================================
    s1_top = y
    row_h = 5 * mm
    data_h = 10 * mm

    sector = f"{nc.related_process.code} - {nc.related_process.name}" if nc.related_process else "-"

    # Fila header: Fecha | Sector | OT | Nº Reporte
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.5)

    # Header row
    c.setFillColor(colors.HexColor("#f0f0f0"))
    c.rect(CONTENT_L, y - row_h, CONTENT_W, row_h, fill=1, stroke=1)
    c.setFillColor(colors.black)
    cols = [0.15, 0.40, 0.25, 0.20]
    x = CONTENT_L
    labels = ["Fecha", "Sector", "Orden de Trabajo", "Nº Reporte"]
    for i, (w, lbl) in enumerate(zip(cols, labels)):
        cw = CONTENT_W * w
        if i > 0:
            c.line(x, y, x, y - row_h)
        c.setFont(FONT_B, 7)
        c.drawString(x + 2 * mm, y - row_h + 1.5 * mm, lbl)
        x += cw
    y -= row_h

    # Data row
    c.rect(CONTENT_L, y - data_h, CONTENT_W, data_h)
    x = CONTENT_L
    values = [_fmt_date(nc.detected_at), sector, _safe(nc.work_order), _safe(nc.code)]
    for i, (w, val) in enumerate(zip(cols, values)):
        cw = CONTENT_W * w
        if i > 0:
            c.line(x, y, x, y - data_h)
        font = FONT_B if i == 3 else FONT
        c.setFont(font, 8)
        if i == 1 and len(val) > 20:
            c.setFont(font, 7)
            mid = val[:30].rfind(" ")
            if mid <= 0:
                mid = 20
            c.drawString(x + 2 * mm, y - 3.5 * mm, val[:mid])
            c.drawString(x + 2 * mm, y - 7 * mm, val[mid:].strip()[:30])
        else:
            c.drawString(x + 2 * mm, y - data_h + 3 * mm, val[:40])
        x += cw
    y -= data_h

    # NC observada durante
    c.rect(CONTENT_L, y - row_h, CONTENT_W, row_h)
    c.line(CONTENT_L + CONTENT_W * 0.4, y, CONTENT_L + CONTENT_W * 0.4, y - row_h)
    c.setFont(FONT_B, 7)
    c.drawString(CONTENT_L + 2 * mm, y - row_h + 1.5 * mm, "No Conformidad observada durante")
    c.setFont(FONT, 8)
    c.drawString(CONTENT_L + CONTENT_W * 0.4 + 2 * mm, y - row_h + 1.5 * mm, _safe(nc.observed_during))
    y -= row_h

    # Norma y Cláusula
    c.rect(CONTENT_L, y - row_h, CONTENT_W, row_h)
    c.line(CONTENT_L + CONTENT_W * 0.4, y, CONTENT_L + CONTENT_W * 0.4, y - row_h)
    c.setFont(FONT_B, 7)
    c.drawString(CONTENT_L + 2 * mm, y - row_h + 1.5 * mm, "Norma y Cláusula:")
    c.setFont(FONT, 8)
    c.drawString(CONTENT_L + CONTENT_W * 0.4 + 2 * mm, y - row_h + 1.5 * mm, _safe(nc.norm_clause))
    y -= row_h

    # NC observada en Proceso
    c.rect(CONTENT_L, y - row_h, CONTENT_W, row_h)
    c.line(CONTENT_L + CONTENT_W * 0.4, y, CONTENT_L + CONTENT_W * 0.4, y - row_h)
    c.setFont(FONT_B, 7)
    c.drawString(CONTENT_L + 2 * mm, y - row_h + 1.5 * mm, "No Conformidad observada en Proceso")
    c.setFont(FONT, 8)
    c.drawString(CONTENT_L + CONTENT_W * 0.4 + 2 * mm, y - row_h + 1.5 * mm, sector[:50])
    y -= row_h

    # Descripción
    c.rect(CONTENT_L, y - desc_h, CONTENT_W, desc_h)
    c.setFont(FONT_B, 7)
    c.drawString(CONTENT_L + 2 * mm, y - 4 * mm, "No Conformidad – Descripción de la Evidencia Objetiva:")
    _draw_multiline(c, CONTENT_L + 3 * mm, y - 8 * mm, nc.description, CONTENT_W - 6 * mm)
    y -= desc_h

    # Categoría | Responsable | Auditor | Representante
    c.setFillColor(colors.HexColor("#f0f0f0"))
    c.rect(CONTENT_L, y - row_h, CONTENT_W, row_h, fill=1, stroke=1)
    c.setFillColor(colors.black)
    cat_cols = [0.2, 0.25, 0.25, 0.3]
    cat_labels = ["Categoría", "Responsable", "Auditor", "Representante de la Org."]
    x = CONTENT_L
    for i, (w, lbl) in enumerate(zip(cat_cols, cat_labels)):
        cw = CONTENT_W * w
        if i > 0:
            c.line(x, y, x, y - row_h)
        c.setFont(FONT_B, 6)
        c.drawString(x + 1.5 * mm, y - row_h + 1.5 * mm, lbl)
        x += cw
    y -= row_h

    c.rect(CONTENT_L, y - data_h, CONTENT_W, data_h)
    cat_values = [
        nc.get_origin_display() if nc.origin else "-",
        _user_name(nc.owner),
        _user_name(nc.detected_by),
        _user_name(nc.organization_representative) if hasattr(nc, 'organization_representative') else "-",
    ]
    x = CONTENT_L
    for i, (w, val) in enumerate(zip(cat_cols, cat_values)):
        cw = CONTENT_W * w
        if i > 0:
            c.line(x, y, x, y - data_h)
        c.setFont(FONT, 8)
        c.drawString(x + 1.5 * mm, y - data_h + 2 * mm, val[:25])
        x += cw
    y -= data_h

    s1_bot = y
    sections["sector"] = (s1_top, s1_bot)

    # ========================================
    # SECCIÓN 2: La Organización
    # ========================================
    s2_top = y

    # Análisis de Causa Raíz
    c.rect(CONTENT_L, y - rca_h, CONTENT_W, rca_h)
    c.setFillColor(colors.HexColor("#f0f0f0"))
    c.rect(CONTENT_L, y - 6 * mm, CONTENT_W, 6 * mm, fill=1, stroke=1)
    c.setFillColor(colors.black)
    c.setFont(FONT_B, 7)
    c.drawString(CONTENT_L + 2 * mm, y - 4 * mm,
                 "Análisis de la Causa Raíz (¿Qué falló en el sistema para permitir que ocurra esta NC?)")
    _draw_multiline(c, CONTENT_L + 3 * mm, y - 10 * mm, nc.root_cause_analysis, CONTENT_W - 6 * mm)
    y -= rca_h

    # Corrección y Acción Correctiva
    c.rect(CONTENT_L, y - ca_h, CONTENT_W, ca_h)
    c.setFillColor(colors.HexColor("#f0f0f0"))
    c.rect(CONTENT_L, y - 6 * mm, CONTENT_W, 6 * mm, fill=1, stroke=1)
    c.setFillColor(colors.black)
    c.setFont(FONT_B, 7)
    c.drawString(CONTENT_L + 2 * mm, y - 4 * mm,
                 "Corrección y Acción Correctiva (Que se hizo para resolver este problema y prevenir la recurrencia)")
    _draw_multiline(c, CONTENT_L + 3 * mm, y - 10 * mm, nc.corrective_action, CONTENT_W - 6 * mm)
    y -= ca_h

    # Verificación de acciones - Fecha de Terminación / Representante
    verif_h = 10 * mm
    c.rect(CONTENT_L, y - verif_h, CONTENT_W, verif_h)
    mid_x = CONTENT_L + CONTENT_W * 0.4
    c.line(mid_x, y, mid_x, y - verif_h)
    c.line(CONTENT_L, y - verif_h / 2, CONTENT_L + CONTENT_W, y - verif_h / 2)

    c.setFont(FONT_B, 7)
    c.drawString(CONTENT_L + 2 * mm, y - 4 * mm, "Verificación de las")
    c.drawString(CONTENT_L + 2 * mm, y - 7.5 * mm, "Acciones Correctivas")

    c.setFont(FONT_B, 7)
    c.drawString(mid_x + 2 * mm, y - 4 * mm, "Fecha de Terminación:")
    c.setFont(FONT, 8)
    c.drawString(mid_x + 35 * mm, y - 4 * mm, _fmt_date(nc.closed_date))

    c.setFont(FONT_B, 7)
    c.drawString(mid_x + 2 * mm, y - 8 * mm, "Representante:")
    c.setFont(FONT, 8)
    rep_name = _user_name(nc.verification_representative) if hasattr(nc, 'verification_representative') else "-"
    c.drawString(mid_x + 25 * mm, y - 8 * mm, rep_name)
    y -= verif_h

    s2_bot = y
    sections["org"] = (s2_top, s2_bot)

    # ========================================
    # SECCIÓN 3: El Auditor
    # ========================================
    s3_top = y

    # Verificación - celda unida izquierda + 3 columnas derecha
    verif_block_h = 12 * mm
    c.rect(CONTENT_L, y - verif_block_h, CONTENT_W, verif_block_h)

    # Columna izquierda: "Verificación de las Acciones Correctivas" (ocupa toda la altura)
    left_col_w = CONTENT_W * 0.3
    c.line(CONTENT_L + left_col_w, y, CONTENT_L + left_col_w, y - verif_block_h)
    c.setFont(FONT_B, 7)
    c.drawString(CONTENT_L + 2 * mm, y - 4.5 * mm, "Verificación de las")
    c.drawString(CONTENT_L + 2 * mm, y - 8.5 * mm, "Acciones Correctivas")

    # Headers derecha
    right_start = CONTENT_L + left_col_w
    right_w = CONTENT_W - left_col_w
    r_cols = [0.33, 0.33, 0.34]
    r_labels = ["Fecha", "Estado", "Auditor"]

    # Línea horizontal dividiendo headers de datos
    c.line(right_start, y - verif_block_h / 2, CONTENT_L + CONTENT_W, y - verif_block_h / 2)

    # Fondo gris para headers derecha
    c.setFillColor(colors.HexColor("#f0f0f0"))
    c.rect(right_start, y - verif_block_h / 2, right_w, verif_block_h / 2, fill=1, stroke=1)
    c.setFillColor(colors.black)

    # Redibujar líneas sobre el fondo
    c.line(CONTENT_L + left_col_w, y, CONTENT_L + left_col_w, y - verif_block_h)
    c.line(right_start, y - verif_block_h / 2, CONTENT_L + CONTENT_W, y - verif_block_h / 2)

    # Líneas verticales y headers
    rx = right_start
    for i, (w, lbl) in enumerate(zip(r_cols, r_labels)):
        cw = right_w * w
        if i > 0:
            c.line(rx, y, rx, y - verif_block_h)
        c.setFont(FONT_B, 6)
        c.drawString(rx + 1.5 * mm, y - 4.5 * mm, lbl)
        rx += cw

    # Datos
    verif_date = _fmt_date(nc.verification_date) if hasattr(nc, 'verification_date') and nc.verification_date else ""
    status_text = nc.get_status_display() if nc.status else "-"
    auditor_name = _user_name(nc.detected_by)
    r_values = [verif_date, status_text, auditor_name]

    rx = right_start
    for i, (w, val) in enumerate(zip(r_cols, r_values)):
        cw = right_w * w
        c.setFont(FONT, 8)
        c.drawString(rx + 1.5 * mm, y - verif_block_h / 2 - 4.5 * mm, val[:25])
        rx += cw

    y -= verif_block_h

    # Comentarios del Auditor
    c.rect(CONTENT_L, y - comments_h, CONTENT_W, comments_h)
    c.setFont(FONT_B, 7)
    c.drawString(CONTENT_L + 2 * mm, y - 4 * mm, "Comentarios del Auditor")
    _draw_multiline(c, CONTENT_L + 3 * mm, y - 8 * mm, nc.verification_notes, CONTENT_W - 6 * mm, max_lines=5)
    y -= comments_h

    s3_bot = y
    sections["auditor"] = (s3_top, s3_bot)

    # ========================================
    # SECCIÓN 4: Responsable de Sistemas
    # ========================================
    s4_top = y

    c.rect(CONTENT_L, y - sys_h, CONTENT_W, sys_h)

    # Fondo gris para primera fila (checkboxes)
    c.setFillColor(colors.HexColor("#f0f0f0"))
    c.rect(CONTENT_L, y - 9 * mm, CONTENT_W, 9 * mm, fill=1, stroke=0)
    c.setFillColor(colors.black)

    label_w = CONTENT_W * 0.45

    # Fondo gris para labels (Descripción / Detectado / Impacta)
    c.setFillColor(colors.HexColor("#f0f0f0"))
    c.rect(CONTENT_L, y - sys_h, label_w, sys_h - 9 * mm, fill=1, stroke=0)
    c.setFillColor(colors.black)

    # Líneas horizontales divisorias dentro de sección 4
    c.line(CONTENT_L, y - 9 * mm, CONTENT_L + CONTENT_W, y - 9 * mm)
    c.line(CONTENT_L, y - 16 * mm, CONTENT_L + CONTENT_W, y - 16 * mm)
    c.line(CONTENT_L, y - 23 * mm, CONTENT_L + CONTENT_W, y - 23 * mm)

    # Línea vertical separando labels de valores
    c.line(CONTENT_L + CONTENT_W * 0.45, y - 9 * mm, CONTENT_L + CONTENT_W * 0.45, y - sys_h)

    # Problema / Hallazgo checkboxes
    is_problem = getattr(nc, 'classification', '') == 'PROBLEM'
    is_finding = getattr(nc, 'classification', '') == 'FINDING'

    cx = CONTENT_L + 3 * mm
    cy = y - 5 * mm
    _draw_checkbox(c, cx, cy, checked=is_problem)
    c.setFont(FONT, 8)
    c.drawString(cx + 11, cy + 1, "Problema")

    _draw_checkbox(c, cx + 30 * mm, cy, checked=is_finding)
    c.drawString(cx + 30 * mm + 11, cy + 1, "Hallazgo")

    # Descripción del problema
    c.setFont(FONT_B, 7)
    c.drawString(CONTENT_L + 3 * mm, y - 13 * mm, "Descripción del problema o hallazgo:")
    c.setFont(FONT, 8)
    c.drawString(CONTENT_L + CONTENT_W * 0.45 + 2 * mm, y - 13 * mm, _safe(nc.title)[:50])

    # Detectado en proceso
    c.setFont(FONT_B, 7)
    c.drawString(CONTENT_L + 3 * mm, y - 20 * mm, "Detectado en proceso o procedimiento:")
    c.setFont(FONT, 8)
    c.drawString(CONTENT_L + CONTENT_W * 0.45, y - 20 * mm, _safe(nc.observed_during)[:50])

    # Impacta en
    c.setFont(FONT_B, 7)
    c.drawString(CONTENT_L + 3 * mm, y - 27 * mm, "Impacta o afecta en:")

    ix = CONTENT_L + CONTENT_W * 0.45 + 2 * mm
    iy = y - 28 * mm
    _draw_checkbox(c, ix, iy, checked=getattr(nc, 'impacts_procedure', False))
    c.setFont(FONT, 7)
    c.drawString(ix + 11, iy + 1, "El Procedimiento")

    _draw_checkbox(c, ix + 35 * mm, iy, checked=getattr(nc, 'impacts_system', False))
    c.drawString(ix + 35 * mm + 11, iy + 1, "El Sistema")

    y -= sys_h

    s4_bot = y
    sections["sistemas"] = (s4_top, s4_bot)

    c.line(CONTENT_L, s1_bot, CONTENT_L + CONTENT_W, s1_bot)
    c.line(CONTENT_L, s2_bot, CONTENT_L + CONTENT_W, s2_bot)
    c.line(CONTENT_L, s3_bot, CONTENT_L + CONTENT_W, s3_bot)

    # ========================================
    # FRANJAS LATERALES VERTICALES
    # ========================================
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.5)

    _draw_vertical_text(c, MARGIN_L, sections["sector"][1], sections["sector"][0],
                        "A ser completado por el Responsable de Sector", COLOR_SECTOR)

    _draw_vertical_text(c, MARGIN_L, sections["org"][1], sections["org"][0],
                        "A ser completado por la Organización", COLOR_ORG)

    _draw_vertical_text(c, MARGIN_L, sections["auditor"][1], sections["auditor"][0],
                        "A ser completado por el Auditor", COLOR_AUDITOR)

    _draw_vertical_text(c, MARGIN_L, sections["sistemas"][1], sections["sistemas"][0],
                        "A ser completado por el Responsable de Sistemas", COLOR_SISTEMAS)

    # Borde exterior completo de todo el contenido
    c.setLineWidth(1)
    c.rect(MARGIN_L, s4_bot, PAGE_W - MARGIN_L - MARGIN_R, s1_top - s4_bot)

    c.save()
    buffer.seek(0)
    return buffer


# ============================================================
# GENERADOR PNC
# ============================================================
def generate_pnc_pdf(pnc):
    """Genera PDF formato R-05-01 (PNC) para un Producto/Servicio No Conforme."""
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    c.setTitle(f"R-05-01-PNC_{pnc.code}")

    # Header
    y = _draw_header(c, "Registro de Producto/Servicio No Conforme", "R-05-01 (PNC)")

    # Título
    y -= 8 * mm
    c.setFont(FONT_B, 12)
    c.drawCentredString(PAGE_W / 2, y, "Reporte de Producto/Servicio No Conforme")
    y -= 6 * mm

    content_start_y = y

    fixed_h = (5 + 6.5 + 5 + 5 + 5 + 5 + 6.5 + 6 + 12) * mm
    flex_base = {
        "desc_h": 25 * mm,
        "rca_h": 25 * mm,
        "ca_h": 25 * mm,
        "notes_h": 16 * mm,
        "comments_h": 22 * mm,
        "sys_h": 40 * mm,
    }
    available_h = content_start_y - MARGIN_B
    flex_base_total = sum(flex_base.values())
    scale = 1.0
    if flex_base_total > 0 and available_h > fixed_h:
        scale = max((available_h - fixed_h) / flex_base_total, 1.0)

    desc_h = flex_base["desc_h"] * scale
    rca_h = flex_base["rca_h"] * scale
    ca_h = flex_base["ca_h"] * scale
    notes_h = flex_base["notes_h"] * scale
    comments_h = flex_base["comments_h"] * scale
    sys_h = flex_base["sys_h"] * scale

    sections = {}

    # ========================================
    # SECCIÓN 1: Responsable de Sector
    # ========================================
    s1_top = y
    row_h = 5 * mm
    data_h = 10 * mm

    sector = f"{pnc.related_process.code} - {pnc.related_process.name}" if pnc.related_process else "-"

    # Fecha | Sector | OT | Nº Reporte (headers)
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.5)
    c.setFillColor(colors.HexColor("#f0f0f0"))
    c.rect(CONTENT_L, y - row_h, CONTENT_W, row_h, fill=1, stroke=1)
    c.setFillColor(colors.black)
    cols = [0.15, 0.40, 0.25, 0.20]
    labels = ["Fecha", "Sector", "Orden de Trabajo", "Nº Reporte"]
    x = CONTENT_L
    for i, (w, lbl) in enumerate(zip(cols, labels)):
        cw = CONTENT_W * w
        if i > 0:
            c.line(x, y, x, y - row_h)
        c.setFont(FONT_B, 7)
        c.drawString(x + 2 * mm, y - row_h + 1.5 * mm, lbl)
        x += cw
    y -= row_h

    # Fecha | Sector | OT | Nº Reporte (datos)
    c.rect(CONTENT_L, y - data_h, CONTENT_W, data_h)
    values = [_fmt_date(pnc.detected_at), sector, _safe(pnc.work_order) if hasattr(pnc, 'work_order') else "-", _safe(pnc.code)]
    x = CONTENT_L
    for i, (w, val) in enumerate(zip(cols, values)):
        cw = CONTENT_W * w
        if i > 0:
            c.line(x, y, x, y - data_h)
        font = FONT_B if i == 3 else FONT
        c.setFont(font, 8)
        if i == 1 and len(val) > 20:
            c.setFont(font, 7)
            mid = val[:30].rfind(" ")
            if mid <= 0:
                mid = 20
            c.drawString(x + 2 * mm, y - 3.5 * mm, val[:mid])
            c.drawString(x + 2 * mm, y - 7 * mm, val[mid:].strip()[:30])
        else:
            c.drawString(x + 2 * mm, y - data_h + 3 * mm, val[:40])
        x += cw
    y -= data_h

    # Producto/Servicio No Conforme
    c.rect(CONTENT_L, y - row_h, CONTENT_W, row_h)
    c.line(CONTENT_L + CONTENT_W * 0.35, y, CONTENT_L + CONTENT_W * 0.35, y - row_h)
    c.setFont(FONT_B, 7)
    c.drawString(CONTENT_L + 2 * mm, y - row_h + 1.5 * mm, "Producto/Servicio No Conforme")
    c.setFont(FONT, 8)
    c.drawString(CONTENT_L + CONTENT_W * 0.35 + 2 * mm, y - row_h + 1.5 * mm, _safe(pnc.product_or_service)[:50])
    y -= row_h

    # Observada durante
    c.rect(CONTENT_L, y - row_h, CONTENT_W, row_h)
    c.line(CONTENT_L + CONTENT_W * 0.35, y, CONTENT_L + CONTENT_W * 0.35, y - row_h)
    c.setFont(FONT_B, 7)
    c.drawString(CONTENT_L + 2 * mm, y - row_h + 1.5 * mm, "Observada durante")
    c.setFont(FONT, 8)
    c.drawString(CONTENT_L + CONTENT_W * 0.35 + 2 * mm, y - row_h + 1.5 * mm,
                 _safe(pnc.observed_during) if hasattr(pnc, 'observed_during') else "-")
    y -= row_h

    # Norma y Cláusula
    c.rect(CONTENT_L, y - row_h, CONTENT_W, row_h)
    c.line(CONTENT_L + CONTENT_W * 0.35, y, CONTENT_L + CONTENT_W * 0.35, y - row_h)
    c.setFont(FONT_B, 7)
    c.drawString(CONTENT_L + 2 * mm, y - row_h + 1.5 * mm, "Norma y Cláusula:")
    c.setFont(FONT, 8)
    c.drawString(CONTENT_L + CONTENT_W * 0.35 + 2 * mm, y - row_h + 1.5 * mm,
                 _safe(pnc.norm_clause) if hasattr(pnc, 'norm_clause') else "-")
    y -= row_h

    # Descripción del No Cumplimiento
    c.rect(CONTENT_L, y - desc_h, CONTENT_W, desc_h)
    c.setFont(FONT_B, 7)
    c.drawString(CONTENT_L + 2 * mm, y - 4 * mm, "Descripción del No Cumplimiento:")
    _draw_multiline(c, CONTENT_L + 3 * mm, y - 8 * mm, pnc.description, CONTENT_W - 6 * mm)
    y -= desc_h

    s1_bot = y
    sections["sector"] = (s1_top, s1_bot)

    # ========================================
    # SECCIÓN 2: La Organización
    # ========================================
    s2_top = y

    # Análisis de Causa Raíz
    c.rect(CONTENT_L, y - rca_h, CONTENT_W, rca_h)
    c.setFillColor(colors.HexColor("#f0f0f0"))
    c.rect(CONTENT_L, y - 6 * mm, CONTENT_W, 6 * mm, fill=1, stroke=1)
    c.setFillColor(colors.black)
    c.setFont(FONT_B, 7)
    c.drawString(CONTENT_L + 2 * mm, y - 4 * mm,
                 "Análisis de la Causa Raíz (¿Qué falló en el sistema para permitir que ocurra este PNC?)")
    rca_text = _safe(pnc.root_cause_analysis, "") if hasattr(pnc, 'root_cause_analysis') else ""
    _draw_multiline(c, CONTENT_L + 3 * mm, y - 10 * mm, rca_text, CONTENT_W - 6 * mm)
    y -= rca_h

    # Corrección y Acción Correctiva
    c.rect(CONTENT_L, y - ca_h, CONTENT_W, ca_h)
    c.setFillColor(colors.HexColor("#f0f0f0"))
    c.rect(CONTENT_L, y - 6 * mm, CONTENT_W, 6 * mm, fill=1, stroke=1)
    c.setFillColor(colors.black)
    c.setFont(FONT_B, 7)
    c.drawString(CONTENT_L + 2 * mm, y - 4 * mm,
                 "Corrección y Acción Correctiva (Que se hizo para resolver este problema y prevenir la recurrencia)")
    ca_text = _safe(pnc.corrective_action, "") if hasattr(pnc, 'corrective_action') else ""
    _draw_multiline(c, CONTENT_L + 3 * mm, y - 10 * mm, ca_text, CONTENT_W - 6 * mm)
    y -= ca_h

    # Producto | Cantidad | Disposición | Responsable
    c.line(CONTENT_L, y, CONTENT_L + CONTENT_W, y)
    c.setFillColor(colors.HexColor("#f0f0f0"))
    c.rect(CONTENT_L, y - row_h, CONTENT_W, row_h, fill=1, stroke=1)
    c.setFillColor(colors.black)
    p_cols = [0.25, 0.15, 0.25, 0.35]
    p_labels = ["Severidad", "Cantidad", "Disposición", "Responsable"]
    x = CONTENT_L
    for i, (w, lbl) in enumerate(zip(p_cols, p_labels)):
        cw = CONTENT_W * w
        if i > 0:
            c.line(x, y, x, y - row_h)
        c.setFont(FONT_B, 7)
        c.drawString(x + 1.5 * mm, y - row_h + 1.5 * mm, lbl)
        x += cw
    y -= row_h

    c.rect(CONTENT_L, y - data_h, CONTENT_W, data_h)
    sev = pnc.get_severity_display() if pnc.severity else "-"
    qty = str(int(pnc.quantity)) if pnc.quantity else "-"
    disp = pnc.get_disposition_display() if pnc.disposition else "-"
    resp = _user_name(pnc.responsible)
    p_values = [sev, qty, disp, resp]
    x = CONTENT_L
    for i, (w, val) in enumerate(zip(p_cols, p_values)):
        cw = CONTENT_W * w
        if i > 0:
            c.line(x, y, x, y - data_h)
        c.setFont(FONT, 8)
        c.drawString(x + 1.5 * mm, y - data_h + 2 * mm, val[:25])
        x += cw
    y -= data_h

    # Notas sobre Disposición
    c.rect(CONTENT_L, y - notes_h, CONTENT_W, notes_h)
    c.setFont(FONT_B, 7)
    c.drawString(CONTENT_L + 2 * mm, y - 4 * mm, "Notas sobre Disposición")
    _draw_multiline(c, CONTENT_L + 3 * mm, y - 8 * mm, pnc.disposition_notes, CONTENT_W - 6 * mm, max_lines=3)
    y -= notes_h

    # Fecha de Cierre / Representante
    close_h = 6 * mm
    c.rect(CONTENT_L, y - close_h, CONTENT_W, close_h)
    c.line(CONTENT_L + CONTENT_W * 0.5, y, CONTENT_L + CONTENT_W * 0.5, y - close_h)
    c.setFont(FONT_B, 7)
    c.drawString(CONTENT_L + 2 * mm, y - close_h + 2 * mm, f"Fecha de Cierre: {_fmt_date(pnc.closed_at)}")
    rep_name = _user_name(pnc.verification_representative) if hasattr(pnc, 'verification_representative') else "-"
    c.drawString(CONTENT_L + CONTENT_W * 0.5 + 2 * mm, y - close_h + 2 * mm, f"Representante: {rep_name}")
    y -= close_h

    s2_bot = y
    sections["org"] = (s2_top, s2_bot)

    # ========================================
    # SECCIÓN 3: El Auditor
    # ========================================
    s3_top = y

    # Verificación - celda unida izquierda + 3 columnas derecha
    verif_block_h = 12 * mm
    c.rect(CONTENT_L, y - verif_block_h, CONTENT_W, verif_block_h)

    # Columna izquierda: "Verificación de las Acciones Correctivas" (ocupa toda la altura)
    left_col_w = CONTENT_W * 0.3
    c.line(CONTENT_L + left_col_w, y, CONTENT_L + left_col_w, y - verif_block_h)
    c.setFont(FONT_B, 7)
    c.drawString(CONTENT_L + 2 * mm, y - 4.5 * mm, "Verificación de las")
    c.drawString(CONTENT_L + 2 * mm, y - 8.5 * mm, "Acciones Correctivas")

    # Headers derecha
    right_start = CONTENT_L + left_col_w
    right_w = CONTENT_W - left_col_w
    r_cols = [0.33, 0.33, 0.34]
    r_labels = ["Fecha", "Estado", "Auditor"]

    # Línea horizontal dividiendo headers de datos
    c.line(right_start, y - verif_block_h / 2, CONTENT_L + CONTENT_W, y - verif_block_h / 2)

    # Fondo gris para headers derecha
    c.setFillColor(colors.HexColor("#f0f0f0"))
    c.rect(right_start, y - verif_block_h / 2, right_w, verif_block_h / 2, fill=1, stroke=1)
    c.setFillColor(colors.black)

    # Redibujar líneas sobre el fondo
    c.line(CONTENT_L + left_col_w, y, CONTENT_L + left_col_w, y - verif_block_h)
    c.line(right_start, y - verif_block_h / 2, CONTENT_L + CONTENT_W, y - verif_block_h / 2)

    # Líneas verticales y headers
    rx = right_start
    for i, (w, lbl) in enumerate(zip(r_cols, r_labels)):
        cw = right_w * w
        if i > 0:
            c.line(rx, y, rx, y - verif_block_h)
        c.setFont(FONT_B, 6)
        c.drawString(rx + 1.5 * mm, y - 4.5 * mm, lbl)
        rx += cw

    # Datos
    verif_date = _fmt_date(pnc.verification_date) if hasattr(pnc, 'verification_date') and pnc.verification_date else ""
    status_text = pnc.get_status_display() if pnc.status else "-"
    auditor_name = _user_name(pnc.detected_by)
    r_values = [verif_date, status_text, auditor_name]

    rx = right_start
    for i, (w, val) in enumerate(zip(r_cols, r_values)):
        cw = right_w * w
        c.setFont(FONT, 8)
        c.drawString(rx + 1.5 * mm, y - verif_block_h / 2 - 4.5 * mm, val[:25])
        rx += cw

    y -= verif_block_h

    # Comentarios del Auditor
    c.rect(CONTENT_L, y - comments_h, CONTENT_W, comments_h)
    c.setFont(FONT_B, 7)
    c.drawString(CONTENT_L + 2 * mm, y - 4 * mm, "Comentarios del Auditor")
    v_notes = _safe(pnc.verification_notes, "") if hasattr(pnc, 'verification_notes') else ""
    _draw_multiline(c, CONTENT_L + 3 * mm, y - 8 * mm, v_notes, CONTENT_W - 6 * mm, max_lines=5)
    y -= comments_h

    s3_bot = y
    sections["auditor"] = (s3_top, s3_bot)

    # ========================================
    # SECCIÓN 4: Responsable de Sistemas
    # ========================================
    s4_top = y

    c.rect(CONTENT_L, y - sys_h, CONTENT_W, sys_h)

    # Fondo gris para primera fila (checkboxes)
    c.setFillColor(colors.HexColor("#f0f0f0"))
    c.rect(CONTENT_L, y - 9 * mm, CONTENT_W, 9 * mm, fill=1, stroke=0)
    c.setFillColor(colors.black)

    label_w = CONTENT_W * 0.45

    # Fondo gris para labels (Descripción / Detectado / Impacta)
    c.setFillColor(colors.HexColor("#f0f0f0"))
    c.rect(CONTENT_L, y - sys_h, label_w, sys_h - 9 * mm, fill=1, stroke=0)
    c.setFillColor(colors.black)

    # Líneas horizontales divisorias dentro de sección 4
    c.line(CONTENT_L, y - 9 * mm, CONTENT_L + CONTENT_W, y - 9 * mm)
    c.line(CONTENT_L, y - 16 * mm, CONTENT_L + CONTENT_W, y - 16 * mm)
    c.line(CONTENT_L, y - 23 * mm, CONTENT_L + CONTENT_W, y - 23 * mm)

    # Línea vertical separando labels de valores
    c.line(CONTENT_L + CONTENT_W * 0.45, y - 9 * mm, CONTENT_L + CONTENT_W * 0.45, y - sys_h)

    # Checkboxes Problema / Hallazgo
    classification = getattr(pnc, 'classification', '')
    is_problem = classification == 'PROBLEM'
    is_finding = classification == 'FINDING'

    cx = CONTENT_L + 3 * mm
    cy = y - 5 * mm
    _draw_checkbox(c, cx, cy, checked=is_problem)
    c.setFont(FONT, 8)
    c.drawString(cx + 11, cy + 1, "Problema")

    _draw_checkbox(c, cx + 30 * mm, cy, checked=is_finding)
    c.drawString(cx + 30 * mm + 11, cy + 1, "Hallazgo")

    # Descripción del problema
    c.setFont(FONT_B, 7)
    c.drawString(CONTENT_L + 3 * mm, y - 13 * mm, "Descripción del problema o hallazgo:")
    c.setFont(FONT, 8)
    c.drawString(CONTENT_L + CONTENT_W * 0.45 + 2 * mm, y - 13 * mm, _safe(pnc.product_or_service)[:50])

    # Detectado en proceso
    c.setFont(FONT_B, 7)
    c.drawString(CONTENT_L + 3 * mm, y - 20 * mm, "Detectado en proceso o procedimiento:")
    c.setFont(FONT, 8)
    obs = _safe(pnc.observed_during) if hasattr(pnc, 'observed_during') else "-"
    c.drawString(CONTENT_L + CONTENT_W * 0.45 + 2 * mm, y - 20 * mm, obs[:50])

    # Impacta en
    c.setFont(FONT_B, 7)
    c.drawString(CONTENT_L + 3 * mm, y - 27 * mm, "Impacta o afecta en:")

    ix = CONTENT_L + CONTENT_W * 0.45 + 2 * mm
    iy = y - 28 * mm
    _draw_checkbox(c, ix, iy, checked=getattr(pnc, 'impacts_procedure', False))
    c.setFont(FONT, 7)
    c.drawString(ix + 11, iy + 1, "El Procedimiento")

    _draw_checkbox(c, ix + 35 * mm, iy, checked=getattr(pnc, 'impacts_system', False))
    c.drawString(ix + 35 * mm + 11, iy + 1, "El Sistema")

    y -= sys_h

    s4_bot = y
    sections["sistemas"] = (s4_top, s4_bot)

    c.line(CONTENT_L, s1_bot, CONTENT_L + CONTENT_W, s1_bot)
    c.line(CONTENT_L, s2_bot, CONTENT_L + CONTENT_W, s2_bot)
    c.line(CONTENT_L, s3_bot, CONTENT_L + CONTENT_W, s3_bot)

    # ========================================
    # FRANJAS LATERALES VERTICALES
    # ========================================
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.5)

    _draw_vertical_text(c, MARGIN_L, sections["sector"][1], sections["sector"][0],
                        "A ser completado por el Responsable de Sector", COLOR_SECTOR)

    _draw_vertical_text(c, MARGIN_L, sections["org"][1], sections["org"][0],
                        "A ser completado por la Organización", COLOR_ORG)

    _draw_vertical_text(c, MARGIN_L, sections["auditor"][1], sections["auditor"][0],
                        "A ser completado por el Auditor", COLOR_AUDITOR)

    _draw_vertical_text(c, MARGIN_L, sections["sistemas"][1], sections["sistemas"][0],
                        "A ser completado por el Responsable de Sistemas", COLOR_SISTEMAS)

    # Borde exterior
    c.setLineWidth(1)
    c.rect(MARGIN_L, s4_bot, PAGE_W - MARGIN_L - MARGIN_R, s1_top - s4_bot)

    c.save()
    buffer.seek(0)
    return buffer