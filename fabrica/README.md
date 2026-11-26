# Estación de fábrica

Programa que corre en el PC que tiene el lector NFC por USB. Por cada matera:

1. Le pide al backend una matera nueva (`POST /api/fabrica/materas`, cabecera `X-Fabrica-Clave`). El backend guarda solo los hashes y devuelve, una única vez, el **token del ESP32** y la **URL del sticker** (`reclamar.html?codigo=…&clave=…`).
2. Graba esa URL como registro NDEF en un sticker virgen (NTAG213/215/216) y la relee para verificarla. Si falla, **descarta** la matera (`DELETE`) para que no quede una sin sticker.
3. Genera `salida/<CODIGO>.h`: el `config.h` del firmware (WiFi, servidor, código y token).
4. Guarda `../materas_fabricadas/<CODIGO>.json` para poder probarla con `simulador_esp32.py`.

El sticker solo lleva la URL con la clave de reclamo. **El token del ESP32 nunca va en el sticker**: cualquiera que lo toque podría leerlo.

## Instalación

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
```

En `.env`: `FABRICA_CLAVE` igual a la de `backend/.env`, `ESP_SERVIDOR` con la IP del PC en la red (no `localhost`: para el ESP32 es él mismo) y el WiFi. Para que el teléfono pueda abrir el sticker, `FRONT_URL` en `backend/.env` también debe usar la IP del PC.

## Uso

```bash
.venv/bin/python estacion.py --especie potos              # varias seguidas, con el lector USB
.venv/bin/python estacion.py --especie potos --una        # una sola
.venv/bin/python estacion.py --especie potos --simular    # sin lector, para probar el flujo
```

Opciones: `--forzar` sobrescribe stickers que ya tengan datos; `--bloquear` deja el sticker de solo lectura (**irreversible**, solo para producción).

## Lector USB en Linux

El ACR122U lo toma el módulo del kernel `pn533_usb` y nfcpy no lo puede abrir. Sacarlo con:

```bash
sudo modprobe -r pn533_usb pn533 nfc
```

Si dice que no tiene permiso, nfcpy imprime la regla udev que hay que agregar (`python -m nfc` la muestra).

## Tests

```bash
.venv/bin/python -m pytest -q tests
```
