# UnihikerSimple

Aplicacion pygame para UniHiker con soporte de multiples vistas. La vista original
`homeload` ahora vive dentro de un orquestador y se puede cambiar con los botones
A y B.

## Ejecutar

```bash
python main.py
```

Tambien sigue funcionando el punto de entrada antiguo:

```bash
python homeload.py
```

## Controles

- `A`: vista siguiente.
- `B`: vista anterior.
- `Left` / `Right`: equivalentes para probar en escritorio.
- `PageUp` / `PageDown`: equivalentes adicionales.
- `N`: lanza una notificacion de prueba en escritorio.
- `Esc` o `Q`: salir.

Si tu imagen de UniHiker emite otros codigos de tecla para los botones fisicos,
ajusta `PREVIOUS_KEYS` y `NEXT_KEYS` en `unihiker/app.py`.

La documentacion oficial de UniHiker indica que A y B estan mapeados tambien
como botones de teclado, por lo que se pueden leer desde pygame:
https://www.unihiker.com/wiki/LanguageReference/PinPong_Library/FunctionOnboard/2_Button_A_and_Button_B/

## Estructura

```text
.
|-- main.py             # Registro de vistas y punto de entrada recomendado
|-- homeload.py         # Launcher de compatibilidad
|-- config.json         # Configuracion local generada/editable
|-- unihiker/
|   |-- app.py          # Bucle principal, navegacion y cambio automatico
|   |-- config.py       # Lectura/escritura de configuracion
|   |-- notifications.py # Overlay global de notificaciones
|   |-- paths.py        # Rutas compartidas del proyecto
|   |-- services/       # Clientes externos con cache local
|   |   |-- buzzer.py
|   |   |-- investments.py
|   |   |-- quote.py
|   |   `-- weather.py
|   `-- views/          # Pantallas del carrusel y configuracion
|       |-- base.py
|       |-- homeload.py
|       |-- clock.py
|       |-- investment.py
|       |-- quote.py
|       `-- settings.py
|-- tools/
|   `-- test_buzzer.py  # Prueba manual del buzzer/audio en la UniHiker
`-- README.md
```

## Crear una vista nueva

1. Crea un archivo en `unihiker/views/`, por ejemplo `unihiker/views/weather.py`.
2. Hereda de `View`.
3. Implementa al menos `draw(self, screen)`.
4. Registrala en `main.py`.

Ejemplo minimo:

```python
import pygame

from .base import View


class WeatherView(View):
    name = "weather"

    def draw(self, screen):
        screen.fill((0, 0, 0))
```

Despues en `main.py`:

```python
from unihiker.views.weather import WeatherView

app = UnihikerApp(
    views=[
        HomeLoadView(),
        ClockView(),
        WeatherView(),
    ]
)
```

## Ciclo de vida de una vista

Cada vista puede implementar estos metodos:

- `on_mount(app)`: se llama una vez al arrancar. Buen sitio para crear fuentes y superficies.
- `on_enter()`: se llama cada vez que la vista pasa a primer plano.
- `on_exit()`: se llama al abandonar la vista.
- `handle_event(event)`: recibe eventos que no consume el orquestador.
- `update(dt)`: logica por frame. `dt` esta en segundos.
- `draw(screen)`: dibuja la vista actual.

La navegacion global vive en `unihiker/app.py`, asi que cada vista puede centrarse en su
propia pantalla.

## Notificaciones

La app tiene una capa global de notificaciones en `unihiker/notifications.py`.
Las notificaciones aparecen como una caja desplegable desde la parte superior,
ocupando aproximadamente el 20% de la pantalla, al estilo de un telefono.

Para probarlo en PC, pulsa `N`. Cada pulsacion alterna entre `info`,
`notice`, `warning` y `critical`.

Desde cualquier parte que tenga acceso a `app`, se puede lanzar una notificacion:

```python
app.notifications.push(
    "Correo",
    "Nuevo mensaje importante",
    level="info",
)
```

Niveles preparados:

- `info`: aviso normal; se cierra solo.
- `notice`: aviso visible hasta tocar la pantalla.
- `warning`: aviso que conviene mirar; se cierra tocando la pantalla.
- `critical`: aviso importante; se cierra tocando la pantalla.

La idea para fuentes externas es que servicios futuros como Gmail, YouTube,
Home Assistant, Telegram o webhooks conviertan sus eventos a este formato comun:
`title`, `message` y `level`.

## Cambio automatico

Las vistas del carrusel cambian automaticamente cada 5 minutos por defecto.
Pulsa `A+B` a la vez para abrir la vista de configuracion. En esa pantalla:

- `A`: suma 30 segundos.
- `B`: resta 30 segundos.
- `A+B`: vuelve al carrusel.

El valor se guarda en `config.json` cuando se cambia desde la vista de
configuracion. Si el archivo no existe, se usa el valor por defecto.

## Clima

La vista del reloj muestra clima actual con Open-Meteo, sin API key. Por defecto
usa Benalmadena y refresca cada 15 minutos. Puedes cambiar estos valores en
`config.json`:

```json
{
  "weather_label": "Benalmadena",
  "weather_latitude": 36.5988,
  "weather_longitude": -4.5168,
  "weather_refresh_seconds": 900
}
```

## Buzzer

La UniHiker tiene buzzer integrado. La app no lo usa todavia, pero queda
preparado para futuras alertas o confirmaciones sonoras.

La configuracion incluye el interruptor apagado por defecto:

```json
{
  "buzzer_enabled": false
}
```

Para comprobar el hardware en la placa:

```bash
python3 tools/test_buzzer.py
```

Usa `python3`, no `uv run`, porque PinPong suele estar instalado en el Python
del sistema de la UniHiker y no dentro de la `.venv` creada por `uv`.

Para usarlo en una vista o en `app.py` mas adelante:

```python
from unihiker.services.buzzer import BuzzerClient

buzzer = BuzzerClient(enabled=app.config["buzzer_enabled"])
buzzer.beep()
```

El servicio importa PinPong de forma diferida. Si se ejecuta en escritorio o en
una venv sin PinPong, no rompe la app: simplemente deja el buzzer como no
disponible.

Cuando `buzzer_enabled` esta en `true`, las notificaciones usan patrones
sonoros distintos:

- `info`: pitido corto.
- `notice`: dos tonos ascendentes.
- `warning`: tres tonos descendentes.
- `critical`: patron urgente alterno.

## Inversion

La vista de inversion muestra la evolucion del Fidelity MSCI World Index Fund
EUR P Acc desde el 16/05/2025. Usa el simbolo de Yahoo Finance `0P0001CLDK.F`
y cachea los datos en `.cache/`.

## Frase Del Dia

La vista de frase usa la API publica:

```text
https://frasedeldia.azurewebsites.net/api/phrase
```

Formato esperado:

```json
{
  "phrase": "A la velocidad de la luz, todos se fusionan con todos. La identidad privada desaparece.",
  "author": "Herbert Marshall McLuhan"
}
```

Se refresca una vez al dia y cachea el ultimo resultado en `.cache/`.

## TODO
- Home Assistant
- Calendario/eventos
