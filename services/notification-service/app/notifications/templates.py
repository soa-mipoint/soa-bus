from html import escape


BRAND_LOGO_URL = "https://www.mipoint.com.pe/logo.png"
BRAND_HOME_URL = "https://www.mipoint.com.pe"

COLOR_BLUE = "#0b3aa9"
COLOR_BLUE_DARK = "#07317f"
COLOR_YELLOW = "#fff200"
COLOR_TEXT = "#25324b"
COLOR_MUTED = "#667085"
COLOR_BORDER = "#e5e9f2"
COLOR_BACKGROUND = "#f5f7fb"


def _hidden_preview(preview_text: str) -> str:
    preview = escape(preview_text)
    return f"""
    <div style="display:none;max-height:0;overflow:hidden;opacity:0;color:transparent;line-height:1px;font-size:1px;">
      {preview}
    </div>
    """


def _button(label: str, href: str = BRAND_HOME_URL) -> str:
    return f"""
    <table role="presentation" cellpadding="0" cellspacing="0" style="margin:24px 0 8px 0;">
      <tr>
        <td style="background:{COLOR_YELLOW};border-radius:14px;text-align:center;">
          <a href="{escape(href)}"
             style="display:inline-block;padding:14px 24px;color:#111827;font-family:Arial,Helvetica,sans-serif;font-size:15px;font-weight:700;text-decoration:none;">
            {escape(label)}
          </a>
        </td>
      </tr>
    </table>
    """


def _detail_row(label: str, value: str, *, is_status: bool = False, is_last: bool = False) -> str:
    border = "none" if is_last else f"1px solid {COLOR_BORDER}"
    value_color = COLOR_BLUE_DARK if is_status else COLOR_TEXT
    return f"""
    <tr>
      <td valign="top" style="padding:13px 16px;border-bottom:{border};font-family:Arial,Helvetica,sans-serif;font-size:14px;line-height:20px;color:{COLOR_MUTED};">
        {escape(label)}
      </td>
      <td align="right" valign="top" style="padding:13px 16px;border-bottom:{border};font-family:Arial,Helvetica,sans-serif;font-size:14px;line-height:20px;color:{value_color};font-weight:700;text-align:right;">
        {escape(value)}
      </td>
    </tr>
    """


def _details_table(rows: list[tuple[str, str]], status_label: str) -> str:
    rendered_rows = []
    last_index = len(rows) - 1
    for index, (label, value) in enumerate(rows):
        rendered_rows.append(
            _detail_row(
                label,
                value,
                is_status=label == status_label,
                is_last=index == last_index,
            )
        )
    return f"""
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:separate;border-spacing:0;background:#ffffff;border:1px solid {COLOR_BORDER};border-radius:14px;overflow:hidden;">
      {''.join(rendered_rows)}
    </table>
    """


def _layout(preview_text: str, title: str, body_html: str, footer_note: str | None = None) -> str:
    note = footer_note or "Este correo fue enviado automaticamente por MiPoint porque realizaste una accion en la plataforma."
    return f"""
    <!doctype html>
    <html lang="es">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>{escape(title)}</title>
      </head>
      <body style="margin:0;padding:0;background:{COLOR_BACKGROUND};">
        {_hidden_preview(preview_text)}
        <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background:{COLOR_BACKGROUND};margin:0;padding:0;">
          <tr>
            <td align="center" style="padding:28px 16px;">
              <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="max-width:640px;background:#ffffff;border-radius:18px;overflow:hidden;border:1px solid {COLOR_BORDER};">
                <tr>
                  <td style="background:{COLOR_BLUE};padding:24px 32px;">
                    <img src="{BRAND_LOGO_URL}" width="138" alt="MiPoint" style="display:block;border:0;outline:none;text-decoration:none;max-width:138px;height:auto;">
                  </td>
                </tr>
                <tr>
                  <td style="padding:34px 32px 30px 32px;">
                    {body_html}
                  </td>
                </tr>
                <tr>
                  <td style="background:#fbfcff;padding:22px 32px;border-top:1px solid {COLOR_BORDER};">
                    <p style="margin:0 0 8px 0;font-family:Arial,Helvetica,sans-serif;font-size:13px;line-height:20px;color:{COLOR_MUTED};">
                      {escape(note)}
                    </p>
                    <p style="margin:0;font-family:Arial,Helvetica,sans-serif;font-size:13px;line-height:20px;color:{COLOR_MUTED};">
                      MiPoint - Reserva espacios para tus eventos.
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        </table>
      </body>
    </html>
    """


def render_welcome_email(nombre: str) -> str:
    safe_name = escape(nombre or "Usuario")
    body = f"""
    <p style="margin:0 0 10px 0;font-family:Arial,Helvetica,sans-serif;font-size:15px;line-height:24px;color:{COLOR_MUTED};">
      Hola {safe_name},
    </p>
    <h1 style="margin:0 0 14px 0;font-family:Arial,Helvetica,sans-serif;font-size:28px;line-height:36px;color:{COLOR_BLUE_DARK};font-weight:800;">
      Tu cuenta en MiPoint ya esta lista
    </h1>
    <p style="margin:0;font-family:Arial,Helvetica,sans-serif;font-size:16px;line-height:26px;color:{COLOR_TEXT};">
      Ya puedes buscar locales, comparar opciones y reservar espacios para tus eventos desde la plataforma.
    </p>
    {_button("Buscar espacios")}
    <p style="margin:18px 0 0 0;font-family:Arial,Helvetica,sans-serif;font-size:14px;line-height:22px;color:{COLOR_MUTED};">
      Si no creaste esta cuenta, puedes ignorar este mensaje.
    </p>
    """
    return _layout(
        "Tu cuenta de MiPoint fue creada correctamente.",
        "Tu cuenta en MiPoint ya esta lista",
        body,
        "Nota de seguridad: MiPoint nunca te pedira tu contrasena por correo.",
    )


def render_booking_email(
    *,
    title: str,
    greeting_name: str,
    message: str,
    space_nombre: str,
    codigo_reserva: str,
    fecha_inicio: str,
    fecha_fin: str,
    status_label: str,
    cta_label: str,
    motivo: str | None = None,
) -> str:
    safe_name = escape(greeting_name or "Usuario")
    rows = [
        ("Estado", status_label),
        ("Espacio", space_nombre),
        ("Codigo de reserva", codigo_reserva),
        ("Inicio", fecha_inicio),
        ("Fin", fecha_fin),
    ]
    if motivo:
        rows.append(("Motivo de cancelacion", motivo))
    details_table = _details_table(rows, "Estado")
    body = f"""
    <p style="margin:0 0 10px 0;font-family:Arial,Helvetica,sans-serif;font-size:15px;line-height:24px;color:{COLOR_MUTED};">
      Hola {safe_name},
    </p>
    <h1 style="margin:0 0 14px 0;font-family:Arial,Helvetica,sans-serif;font-size:28px;line-height:36px;color:{COLOR_BLUE_DARK};font-weight:800;">
      {escape(title)}
    </h1>
    <p style="margin:0 0 22px 0;font-family:Arial,Helvetica,sans-serif;font-size:16px;line-height:26px;color:{COLOR_TEXT};">
      {escape(message)}
    </p>
    {details_table}
    {_button(cta_label)}
    <p style="margin:18px 0 0 0;font-family:Arial,Helvetica,sans-serif;font-size:14px;line-height:22px;color:{COLOR_MUTED};">
      Conserva este correo como constancia de tu reserva.
    </p>
    """
    return _layout(
        f"{title}: {space_nombre} - codigo {codigo_reserva}.",
        title,
        body,
        "Nota de seguridad: MiPoint nunca te pedira pagos, claves o datos sensibles por correo.",
    )
