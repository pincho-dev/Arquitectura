# Sistema de diagnóstico del estado de plantas

Proyecto de corte — Arquitectura de Software. Servicio que, dadas unas mediciones (humedad, luz, temperatura) y una especie, determina el estado de la planta. Base del producto "matera inteligente".

## Estructura del repositorio

```
backend/     API Flask (dominio, aplicación, presentación, infraestructura)
frontend/    Cliente HTML/CSS/JS estático, servido por separado del backend
docs/        Documento de arquitectura, diagramas y bitácora de uso de IA
```

> TODO (equipo): a medida que se cree la estructura interna de `backend/` (capas domain/application/presentation/infrastructure), documentar aquí el árbol real, para que coincida con el diagrama de paquetes del documento de arquitectura.

## Requisitos previos

- Python 3.10+
- Un navegador (para el front, no requiere Node ni build tool)

## Backend: cómo correrlo

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # y completar los valores (ver .env.example)
# TODO (equipo): comando real de arranque cuando exista el entrypoint, ej.:
# flask --app app run
```

La API queda disponible en `http://localhost:5000` (configurable en `.env`).

## Front: cómo correrlo

El front es HTML/CSS/JS estático, sin build. Basta con servirlo con cualquier servidor estático, por ejemplo:

```bash
cd frontend
python -m http.server 5500
```

Y abrir `http://localhost:5500`. El origen debe coincidir con `CORS_ORIGIN` configurado en el `.env` del backend.

> TODO (equipo): ajustar el puerto/instrucción si terminan usando otra herramienta (Live Server, etc.).

## Tests del dominio

```bash
cd backend
pytest
```

Las pruebas ejercitan la lógica de negocio sin levantar el servidor y sin leer archivo/base de datos reales.

## Documento de arquitectura

Ver [`docs/`](./docs) — incluye el documento de arquitectura y la [bitácora de uso de IA](./docs/BITACORA_IA.md).
