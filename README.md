# Sistema de diagnóstico del estado de plantas

Proyecto de corte — Arquitectura de Software. Servicio que, dadas unas mediciones (humedad, luz, temperatura) y una especie, determina el estado de la planta. Base del producto "matera inteligente".

## Estructura del repositorio

```
backend/     API Flask (dominio, aplicación, presentación, infraestructura)
frontend/    Cliente HTML/CSS/JS estático, servido por separado del backend
docs/        Documento de arquitectura, diagramas y bitácora de uso de IA
fabrica/     Estación de fábrica con lector NFC por USB (graba el sticker y genera el config del ESP32)
firmware/    Firmware del ESP32 (Arduino), conectado por WebSocket
```

Dentro de `backend/`:

```
domain/          Núcleo: modelos, reglas de negocio y puertos (puertos.py = salida, puertos_entrada.py = entrada)
application/     Casos de uso: implementan los puertos de entrada
infrastructure/  Adaptadores de salida: CSV, PostgreSQL, bcrypt, JWT, tokens de dispositivo, canales WebSocket
presentation/    Adaptadores de entrada (API del front, API y WebSocket de dispositivos, API de fábrica),
                 WebSocket de avisos al front y app.py = punto de composición
migrations/      Migraciones de Alembic
tests/           Pruebas con dobles de prueba
```

## Requisitos previos

- Python 3.10+
- Docker (para PostgreSQL) — o un PostgreSQL 16 propio, ajustando `DATABASE_URL`
- Un navegador (para el front, no requiere Node ni build tool)

## Base de datos

```bash
docker compose up -d             # en la raíz del repo: levanta PostgreSQL en localhost:5432
cd backend
alembic upgrade head             # crea las tablas y carga especies (desde el CSV) y roles
```

Para empezar de cero: `docker compose down -v` y de nuevo los dos comandos.

## Backend: cómo correrlo

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # y poner un JWT_SECRET largo y aleatorio
flask --app presentation.app run
```

La API queda disponible en `http://localhost:5000`.

**Tabla de referencia CSV o BD (R4):** en `.env`, `TABLA_REFERENCIA=csv` o `TABLA_REFERENCIA=bd`, y reiniciar el backend. No se toca código.

### Endpoints

| Método y ruta | Auth | Qué hace |
|---|---|---|
| `POST /api/auth/registro` | — | `{nombre, correo, password}` → `{token, usuario}` |
| `POST /api/auth/login` | — | `{correo, password}` → `{token, usuario}` |
| `GET /api/plantas` | JWT usuario | Plantas del usuario con su estado actual |
| `POST /api/plantas` | JWT usuario | `{nombre, especie}` |
| `GET /api/plantas/{id}/estado` | JWT usuario | Estado, última lectura e historial (403 si la planta es ajena) |
| `POST /api/plantas/{id}/lecturas` | JWT usuario | Lectura manual desde el formulario |
| `POST /api/plantas/{id}/duenos` | JWT usuario | `{correo}`: comparte la planta con otro usuario registrado (solo un dueño puede) |
| `POST /api/plantas/reclamar` | JWT usuario | `{codigo, clave}` del sticker NFC: la matera y su planta pasan a ser del usuario |
| `POST /api/plantas/{id}/dispositivos` | JWT usuario | `{codigo}` → token del dispositivo (se muestra una sola vez) |
| `GET /api/dispositivos` | JWT usuario | Materas del usuario (propias y compartidas) con su planta y si están conectadas |
| `POST /api/dispositivos/{codigo}/lecturas` | Token de dispositivo | `{dispositivo, medida_en, humedad, luz, temperatura}` |
| `POST /api/dispositivos/{codigo}/ordenes` | JWT usuario | `{orden, parametros}` → la orden viaja al ESP32 por su WebSocket (`parpadear`, `reportar`, `regar {segundos}`); 409 si no está conectada |
| `POST /api/fabrica/materas` | `X-Fabrica-Clave` | `{especie, codigo?}` → token del firmware y URL del sticker (lo usa `fabrica/estacion.py`) |
| `DELETE /api/fabrica/materas/{codigo}` | `X-Fabrica-Clave` | Descarta una matera que nadie reclamó (falló la grabación del sticker) |
| `WS /ws/dispositivos` | Token de dispositivo (1.er mensaje) | Conexión permanente del ESP32: lecturas, órdenes y presencia en vivo |
| `WS /ws/app` | JWT usuario (1.er mensaje) | Avisos en vivo al front: lecturas, conexión/desconexión de materas, órdenes cumplidas |
| `POST /diagnostico`, `GET /especies` | — | Endpoints de la fase 1 |

## Materas con sticker NFC (fábrica y reclamo simulados)

Cada matera sale de "fábrica" sin dueño: su token va en el firmware y una clave de reclamo en el sticker NFC. Al acercar el teléfono, el sticker abre `reclamar.html?codigo=...&clave=...` y la planta queda agregada a la cuenta del usuario. Mientras nadie la reclame, el backend rechaza sus lecturas.

```bash
cd backend
flask --app presentation.app fabricar-matera --especie potos      # crea materas_fabricadas/MAT-XXXX.json
cd ..
python simulador_esp32.py --matera materas_fabricadas/MAT-XXXX.json --tocar-nfc
```

`--tocar-nfc` abre la URL del sticker en el navegador (el "toque" simulado). Con un sticker real, se graba esa URL con cualquier app de NFC (ej. NFC Tools) y se usa la IP de la red local en `FRONT_URL`.

## Tiempo real con WebSockets

Hay dos WebSockets, y el dominio no sabe que existen:

- **`/ws/dispositivos` (ESP32 → backend):** el ESP32 abre una conexión y la deja abierta. Se presenta con `{"tipo": "hola", "codigo", "token"}`, manda lecturas `{"tipo": "lectura", "humedad", "luz", "temperatura"}` que entran al mismo caso de uso `RegistrarLectura` que el formulario y el POST HTTP, y recibe órdenes `{"tipo": "orden", ...}`. Mientras el socket esté abierto la matera **está** conectada; si se cierra, queda desconectada **al instante**. Si el ESP32 se apaga de golpe y no alcanza a cerrar, el servidor le hace ping cada `WS_PING_S` segundos y corta la conexión cuando no responde.
- **`/ws/app` (backend → front):** el JWT va en el primer mensaje (`{"tipo": "auth", "token"}`) porque el navegador no deja poner la cabecera `Authorization` en un WebSocket. Cada usuario recibe solo avisos de sus plantas (propias y compartidas). `frontend/js/tiempo-real.js` recarga la página con cada aviso y, si el WebSocket se cae, vuelve a la consulta periódica de R6 cada 5 s hasta que se recupere.

Probarlo con el simulador:

```bash
python simulador_esp32.py --matera materas_fabricadas/MAT-XXXX.json --ws
kill -STOP <pid>   # "se va la luz": a los ~2 pings el front la muestra desconectada
kill -CONT <pid>   # vuelve y se reconecta sola
```

Limitación conocida: las conexiones viven en la memoria del proceso (`infrastructure/canal_websocket.py`). Con varios procesos o servidores haría falta un broker (Redis pub/sub o MQTT).

## Estación de fábrica con lector NFC (`fabrica/`)

La versión física de `flask fabricar-matera`: registra la matera en el backend (`POST /api/fabrica/materas`), graba la URL de reclamo en un sticker NFC virgen con un lector USB (ACR122U o compatible con nfcpy), la relee para verificarla y genera `fabrica/salida/<CODIGO>.h`, el `config.h` del firmware. Si la grabación falla, descarta la matera. Ver `fabrica/README.md`.

```bash
cd fabrica && python -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env          # FABRICA_CLAVE igual a la de backend/.env, IP del PC y WiFi del ESP32
.venv/bin/python estacion.py --especie potos            # con el lector USB
.venv/bin/python estacion.py --especie potos --simular  # sin lector
```

## Firmware del ESP32 (`firmware/matera_esp32/`)

Arduino IDE con las bibliotecas **WebSockets** (Markus Sattler) y **ArduinoJson** (Benoit Blanchon), placa *ESP32 Dev Module*. Copiar `config.example.h` como `config.h` (o el `.h` que genera la estación) y subirlo. El `loop()` no usa `delay()`: tiene que llamar `webSocket.loop()` siempre para responder los ping del servidor.

## Simulador del ESP32 (vinculación manual)

1. Con un usuario logueado, crear una planta y vincular un dispositivo (`POST /api/plantas/{id}/dispositivos`); copiar el `token` que devuelve.
2. Desde la raíz del repo (solo librería estándar, no requiere instalar nada):

```bash
python simulador_esp32.py --codigo ESP32-01 --token dev_xxxxx --intervalo 5 --perfil potos
```

Opciones: `--prob-fuera` y `--prob-invalido` (probabilidad de lecturas fuera de rango y de datos inválidos), `--cantidad`, `--semilla`. El token también puede ir en la variable `MATERA_TOKEN_DISPOSITIVO`.

## Front: cómo correrlo

El front es HTML/CSS/JS estático, sin build. Basta con servirlo con cualquier servidor estático, por ejemplo:

```bash
cd frontend
python -m http.server 5500
```

Y abrir `http://localhost:5500`. El origen debe coincidir con `CORS_ORIGIN` configurado en el `.env` del backend.

> TODO (equipo): ajustar el puerto/instrucción si terminan usando otra herramienta (Live Server, etc.).

## Tests

```bash
cd backend
pytest
```

Las pruebas usan dobles de prueba para los puertos de salida: corren sin levantar el servidor y sin archivos ni base de datos.

## Documento de arquitectura

Ver [`docs/`](./docs) — incluye el documento de arquitectura y la [bitácora de uso de IA](./docs/BITACORA_IA.md).
