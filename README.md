# Sistema de diagnóstico del estado de plantas

Proyecto de corte — Arquitectura de Software. Servicio que, dadas unas mediciones (humedad, luz, temperatura) y una especie, determina el estado de la planta. Base del producto "matera inteligente".

## Estructura del repositorio

```
backend/     API Flask (dominio, aplicación, presentación, infraestructura)
frontend/    Cliente HTML/CSS/JS estático, servido por separado del backend
docs/        Documento de arquitectura, diagramas y bitácora de uso de IA
```

Dentro de `backend/`:

```
domain/          Núcleo: modelos, reglas de negocio y puertos (puertos.py = salida, puertos_entrada.py = entrada)
application/     Casos de uso: implementan los puertos de entrada
infrastructure/  Adaptadores de salida: CSV, PostgreSQL, bcrypt, JWT, tokens de dispositivo
presentation/    Adaptadores de entrada (API del front, API de dispositivos) y app.py = punto de composición
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
| `POST /api/plantas/{id}/dispositivos` | JWT usuario | `{codigo}` → token del dispositivo (se muestra una sola vez) |
| `POST /api/dispositivos/{codigo}/lecturas` | Token de dispositivo | `{dispositivo, medida_en, humedad, luz, temperatura}` |
| `POST /diagnostico`, `GET /especies` | — | Endpoints de la fase 1 |

## Simulador del ESP32

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
