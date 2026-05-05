"""Tiny built-in web UI for configuring the UNIHIKER app."""

import html
import json
import threading
import urllib.parse
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from unihiker.config import DEFAULT_CONFIG, save_config


LEVELS = ("info", "notice", "warning", "critical")


FIELD_GROUPS = (
    (
        "General",
        (
            ("auto_switch_seconds", "Cambio automatico (s)", "number"),
            ("web_enabled", "Interfaz web activa", "bool"),
            ("web_host", "Host web", "text"),
            ("web_port", "Puerto web", "number"),
        ),
    ),
    (
        "Clima",
        (
            ("weather_enabled", "Clima activo", "bool"),
            ("weather_label", "Etiqueta", "text"),
            ("weather_latitude", "Latitud", "number"),
            ("weather_longitude", "Longitud", "number"),
            ("weather_refresh_seconds", "Refresco clima (s)", "number"),
        ),
    ),
    (
        "Inversion",
        (
            ("investment_label", "Etiqueta", "text"),
            ("investment_symbol", "Simbolo Yahoo", "text"),
            ("investment_start_date", "Fecha inicio", "date"),
            ("investment_refresh_seconds", "Refresco inversion (s)", "number"),
        ),
    ),
    (
        "Frase",
        (
            ("quote_url", "URL frase", "text"),
            ("quote_refresh_seconds", "Refresco frase (s)", "number"),
        ),
    ),
    (
        "Buzzer",
        (
            ("buzzer_enabled", "Buzzer activo", "bool"),
        ),
    ),
)


def start_web_config_server(app):
    if not app.config.get("web_enabled", True):
        return None

    server = WebConfigServer(app)
    server.start()
    return server


class WebConfigServer:
    def __init__(self, app):
        self.app = app
        self.httpd = None
        self.thread = None

    def start(self):
        host = self.app.config["web_host"]
        port = self.app.config["web_port"]
        handler = self._make_handler()
        try:
            self.httpd = ThreadingHTTPServer((host, port), handler)
        except OSError as exc:
            print(f"Web config disabled: {exc}")
            return

        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        visible_host = "localhost" if host in ("", "0.0.0.0") else host
        print(f"Web config listening on http://{visible_host}:{port}")

    def stop(self):
        if not self.httpd:
            return

        self.httpd.shutdown()
        self.httpd.server_close()
        self.httpd = None

    def _make_handler(self):
        app = self.app

        class Handler(BaseHTTPRequestHandler):
            def do_OPTIONS(self):
                self.send_response(204)
                self._cors_headers()
                self.end_headers()

            def do_GET(self):
                path = urllib.parse.urlparse(self.path).path
                if path == "/":
                    self._send_html(render_page(app, message=self._query_message()))
                elif path == "/api/config":
                    self._send_json(app.config)
                elif path == "/api/state":
                    self._send_json(self._state_payload())
                else:
                    self.send_error(404)

            def do_POST(self):
                path = urllib.parse.urlparse(self.path).path
                if path == "/save":
                    payload = self._read_form()
                    update_config_from_form(app, payload)
                    self._redirect("/?saved=1")
                elif path == "/api/config":
                    payload = self._read_json()
                    update_config(app, payload)
                    self._send_json(app.config)
                elif path == "/notify":
                    payload = self._read_form()
                    push_notification(app, payload)
                    self._redirect("/?notified=1")
                elif path == "/buzzer/test":
                    app.buzzer.sequence((660, 880, 660), beats=1)
                    self._redirect("/?buzzed=1")
                elif path == "/api/notify":
                    payload = self._read_json()
                    push_notification(app, payload)
                    self._send_json({"ok": True})
                elif path == "/api/buzzer/test":
                    app.buzzer.sequence((660, 880, 660), beats=1)
                    self._send_json({"ok": True, "buzzer": app.buzzer.snapshot()})
                else:
                    self.send_error(404)

            def log_message(self, format, *args):
                return

            def _query_message(self):
                query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                if query.get("saved"):
                    return "Configuracion guardada"
                if query.get("notified"):
                    return "Notificacion enviada"
                if query.get("buzzed"):
                    return "Prueba de buzzer enviada"
                return ""

            def _state_payload(self):
                return {
                    "config": app.config,
                    "current_view": app.current_view.name if app.current_view else None,
                    "available_views": app.view_names,
                    "active_views": [view.name for view in app.views],
                    "notifications": app.notifications.snapshot(),
                    "buzzer": app.buzzer.snapshot(),
                }

            def _read_form(self):
                length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(length).decode("utf-8")
                return {
                    key: values[-1]
                    for key, values in urllib.parse.parse_qs(body, keep_blank_values=True).items()
                }

            def _read_json(self):
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0:
                    return {}
                return json.loads(self.rfile.read(length).decode("utf-8"))

            def _redirect(self, location):
                self.send_response(303)
                self.send_header("Location", location)
                self.end_headers()

            def _send_html(self, body):
                data = body.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self._cors_headers()
                self.end_headers()
                self.wfile.write(data)

            def _send_json(self, payload):
                data = json.dumps(payload, indent=2).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self._cors_headers()
                self.end_headers()
                self.wfile.write(data)

            def _cors_headers(self):
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")

        return Handler


def update_config_from_form(app, form):
    values = {}
    for _, fields in FIELD_GROUPS:
        for key, _, field_type in fields:
            if field_type == "bool":
                values[key] = form.get(key) == "on"
            elif key in form:
                values[key] = form[key]
    values["view_order"] = parse_view_order(app, form)
    update_config(app, values)


def update_config(app, values):
    config = dict(app.config)
    for key, value in values.items():
        if key not in DEFAULT_CONFIG:
            continue
        config[key] = coerce_value(key, value)

    app.config.clear()
    app.config.update(config)
    app.apply_view_order(app.config["view_order"])
    app.auto_switch_seconds = app.config["auto_switch_seconds"]
    app.buzzer.set_enabled(app.config["buzzer_enabled"])
    save_config(app.config)


def coerce_value(key, value):
    default = DEFAULT_CONFIG[key]
    if key == "view_order":
        if isinstance(value, list):
            return [str(item) for item in value]
        return list(default)
    if isinstance(default, bool):
        if isinstance(value, str):
            return value.lower() in ("1", "true", "yes", "on")
        return bool(value)
    if isinstance(default, int):
        try:
            return normalize_value(key, int(float(value)))
        except (TypeError, ValueError):
            return default
    if isinstance(default, float):
        try:
            return normalize_value(key, float(value))
        except (TypeError, ValueError):
            return default
    text = str(value)
    if key == "investment_start_date":
        try:
            date.fromisoformat(text)
        except ValueError:
            return default
    return text


def normalize_value(key, value):
    if key == "auto_switch_seconds":
        return max(10, int(value))
    if key == "web_port":
        return min(65535, max(1, int(value)))
    if key == "weather_refresh_seconds":
        return max(60, int(value))
    if key == "investment_refresh_seconds":
        return max(300, int(value))
    if key == "quote_refresh_seconds":
        return max(3600, int(value))
    return value


def push_notification(app, payload):
    title = str(payload.get("title") or "Notificacion")
    message = str(payload.get("message") or "")
    level = str(payload.get("level") or "info")
    app.notifications.push(title, message, level=level)


def parse_view_order(app, form):
    rows = []
    for name in app.view_names:
        if form.get(f"view_enabled_{name}") != "on":
            continue
        try:
            order = int(form.get(f"view_order_{name}", "999"))
        except ValueError:
            order = 999
        rows.append((order, name))

    rows.sort(key=lambda item: (item[0], app.view_names.index(item[1])))
    if not rows:
        return [app.view_names[0]]
    return [name for _, name in rows]


def render_page(app, message=""):
    config = app.config
    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>UnihikerSimple</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #080b10;
      --panel: #101722;
      --line: #253446;
      --text: #edf7f8;
      --muted: #91a6ad;
      --accent: #00e5c8;
      --green: #3dff8f;
      --warn: #ffbe4c;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font: 15px/1.45 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    header {{
      position: sticky;
      top: 0;
      z-index: 2;
      background: rgba(8, 11, 16, .92);
      border-bottom: 1px solid var(--line);
      backdrop-filter: blur(12px);
    }}
    .bar {{
      max-width: 1080px;
      margin: 0 auto;
      padding: 18px 20px;
      display: flex;
      gap: 12px;
      justify-content: space-between;
      align-items: center;
    }}
    h1 {{ margin: 0; font-size: 20px; }}
    main {{
      max-width: 1080px;
      margin: 0 auto;
      padding: 22px 20px 40px;
      display: grid;
      grid-template-columns: 1fr 320px;
      gap: 18px;
    }}
    section {{
      border: 1px solid var(--line);
      background: var(--panel);
      border-radius: 8px;
      padding: 16px;
      margin-bottom: 16px;
    }}
    h2 {{
      margin: 0 0 14px;
      font-size: 14px;
      color: var(--accent);
      text-transform: uppercase;
      letter-spacing: .04em;
    }}
    label {{
      display: grid;
      gap: 6px;
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: .04em;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
    }}
    .views {{
      display: grid;
      gap: 10px;
    }}
    .view-row {{
      display: grid;
      grid-template-columns: 32px 1fr auto;
      gap: 10px;
      align-items: center;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #0a1018;
      padding: 10px;
      cursor: grab;
      user-select: none;
    }}
    .view-row.dragging {{
      opacity: .46;
      border-color: var(--accent);
    }}
    .drag-handle {{
      color: var(--muted);
      font-weight: 800;
      text-align: center;
      cursor: grab;
    }}
    .view-name {{
      color: var(--text);
      font-weight: 700;
      text-transform: none;
      letter-spacing: 0;
      font-size: 14px;
    }}
    input, select, textarea {{
      width: 100%;
      border: 1px solid var(--line);
      background: #0a1018;
      color: var(--text);
      border-radius: 6px;
      padding: 10px 11px;
      font: inherit;
      outline: none;
    }}
    input:focus, select:focus, textarea:focus {{
      border-color: var(--accent);
    }}
    input[type="checkbox"] {{
      width: 18px;
      height: 18px;
      accent-color: var(--accent);
    }}
    .check {{
      display: flex;
      flex-direction: row;
      justify-content: space-between;
      align-items: center;
      min-height: 42px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px 11px;
      background: #0a1018;
    }}
    button, .button {{
      border: 0;
      border-radius: 6px;
      background: var(--accent);
      color: #001716;
      padding: 10px 13px;
      font-weight: 700;
      cursor: pointer;
      text-decoration: none;
      display: inline-flex;
      justify-content: center;
      align-items: center;
      min-height: 40px;
    }}
    .secondary {{
      background: #1c2a38;
      color: var(--text);
      border: 1px solid var(--line);
    }}
    .actions {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }}
    .notice {{
      border-color: #1f594c;
      color: var(--green);
    }}
    .muted {{ color: var(--muted); }}
    .side {{
      position: sticky;
      top: 82px;
      align-self: start;
    }}
    .row {{
      display: flex;
      gap: 10px;
      margin-top: 10px;
    }}
    textarea {{ resize: vertical; min-height: 92px; }}
    code {{
      color: var(--green);
      word-break: break-all;
    }}
    @media (max-width: 760px) {{
      main {{ grid-template-columns: 1fr; }}
      .grid {{ grid-template-columns: 1fr; }}
      .side {{ position: static; }}
      .bar {{ align-items: flex-start; flex-direction: column; }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="bar">
      <div>
        <h1>UnihikerSimple</h1>
        <div class="muted">Configurar, personalizar y probar notificaciones</div>
      </div>
      <a class="button secondary" href="/api/config">JSON</a>
    </div>
  </header>
  <main>
    <div>
      {render_message(message)}
      <form method="post" action="/save">
        {render_views(app)}
        {render_groups(config)}
        <section>
          <div class="actions">
            <button type="submit">Guardar configuracion</button>
            <a class="button secondary" href="/">Descartar cambios</a>
          </div>
        </section>
      </form>
    </div>
    <aside class="side">
      <section>
        <h2>Notificacion</h2>
        <form method="post" action="/notify">
          <label>Titulo
            <input name="title" value="Web">
          </label>
          <div class="row">
            <label style="flex: 1">Nivel
              <select name="level">
                {render_level_options()}
              </select>
            </label>
          </div>
          <label style="margin-top: 12px">Mensaje
            <textarea name="message">Prueba enviada desde la web</textarea>
          </label>
          <div class="actions" style="margin-top: 12px">
            <button type="submit">Enviar prueba</button>
          </div>
        </form>
      </section>
      <section>
        <h2>Endpoints</h2>
        <p class="muted">Leer configuracion:</p>
        <p><code>GET /api/config</code></p>
        <p class="muted">Enviar notificacion:</p>
        <p><code>POST /api/notify</code></p>
        <p class="muted">Estado basico:</p>
        <p><code>GET /api/state</code></p>
      </section>
      <section>
        <h2>Buzzer</h2>
        <p class="muted">Usa la misma ruta interna que las notificaciones.</p>
        <form method="post" action="/buzzer/test">
          <button type="submit">Probar buzzer</button>
        </form>
      </section>
    </aside>
  </main>
  <script>
    const views = document.querySelector(".views");

    function syncViewOrder() {{
      if (!views) return;
      [...views.querySelectorAll(".view-row")].forEach((row, index) => {{
        const order = row.querySelector("[data-view-order]");
        if (order) order.value = String(index + 1);
      }});
    }}

    function getDragAfterElement(container, y) {{
      const rows = [...container.querySelectorAll(".view-row:not(.dragging)")];
      return rows.reduce((closest, child) => {{
        const box = child.getBoundingClientRect();
        const offset = y - box.top - box.height / 2;
        if (offset < 0 && offset > closest.offset) {{
          return {{ offset, element: child }};
        }}
        return closest;
      }}, {{ offset: Number.NEGATIVE_INFINITY, element: null }}).element;
    }}

    if (views) {{
      views.addEventListener("dragstart", event => {{
        const row = event.target.closest(".view-row");
        if (!row) return;
        row.classList.add("dragging");
        event.dataTransfer.effectAllowed = "move";
      }});

      views.addEventListener("dragend", event => {{
        const row = event.target.closest(".view-row");
        if (row) row.classList.remove("dragging");
        syncViewOrder();
      }});

      views.addEventListener("dragover", event => {{
        event.preventDefault();
        const dragging = views.querySelector(".dragging");
        if (!dragging) return;
        const after = getDragAfterElement(views, event.clientY);
        if (after) {{
          views.insertBefore(dragging, after);
        }} else {{
          views.appendChild(dragging);
        }}
      }});

      const form = views.closest("form");
      if (form) form.addEventListener("submit", syncViewOrder);
      syncViewOrder();
    }}
  </script>
</body>
</html>"""


def render_message(message):
    if not message:
        return ""
    return f'<section class="notice">{html.escape(message)}</section>'


def render_views(app):
    active_order = {
        name: index + 1
        for index, name in enumerate(app.config.get("view_order", []))
    }
    active_names = set(active_order)
    rows = []
    names = [
        name for name in app.config.get("view_order", [])
        if name in app.view_names
    ]
    names.extend(name for name in app.view_names if name not in names)

    for index, name in enumerate(names, start=1):
        checked = " checked" if name in active_names else ""
        order = active_order.get(name, index)
        safe_name = html.escape(name)
        rows.append(
            f"<div class=\"view-row\" draggable=\"true\" data-view=\"{safe_name}\">"
            "<div class=\"drag-handle\">::</div>"
            f"<input type=\"hidden\" data-view-order name=\"view_order_{safe_name}\" value=\"{order}\">"
            f"<div class=\"view-name\">{safe_name}</div>"
            f"<input type=\"checkbox\" name=\"view_enabled_{safe_name}\"{checked}>"
            "</div>"
        )

    return (
        "<section><h2>Vistas</h2>"
        "<p class=\"muted\">Arrastra las cajas para cambiar el orden y activa las vistas que quieras mostrar. "
        "Se aplica al pulsar guardar.</p>"
        f"<div class=\"views\">{''.join(rows)}</div></section>"
    )


def render_groups(config):
    return "\n".join(render_group(title, fields, config) for title, fields in FIELD_GROUPS)


def render_group(title, fields, config):
    controls = "\n".join(render_field(key, label, field_type, config.get(key)) for key, label, field_type in fields)
    return f"<section><h2>{html.escape(title)}</h2><div class=\"grid\">{controls}</div></section>"


def render_field(key, label, field_type, value):
    safe_key = html.escape(key)
    safe_label = html.escape(label)
    if field_type == "bool":
        checked = " checked" if value else ""
        return (
            f'<label class="check"><span>{safe_label}</span>'
            f'<input type="checkbox" name="{safe_key}"{checked}></label>'
        )

    input_type = "number" if field_type == "number" else field_type
    step = ' step="any"' if key.endswith(("latitude", "longitude")) else ""
    return (
        f"<label>{safe_label}"
        f'<input type="{input_type}" name="{safe_key}" value="{html.escape(str(value))}"{step}>'
        "</label>"
    )


def render_level_options():
    return "\n".join(f'<option value="{level}">{level}</option>' for level in LEVELS)
