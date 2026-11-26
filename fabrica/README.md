# Estación de fábrica

Programa que corre en el PC de la "fábrica". Por cada matera:

1. **(Opcional, con `--rfid`)** Se acerca al lector RC522 la tarjeta RFID que va pegada a la matera y se lee su UID.
2. Le pide al backend una matera nueva (`POST /api/fabrica/materas`, cabecera `X-Fabrica-Clave`). El backend guarda solo los hashes y devuelve, una única vez, el **token del ESP32** y la **URL de reclamo** (`reclamar.html?codigo=…&clave=…`). Si la tarjeta ya está en otra matera, responde 409 y no se crea nada.
3. Genera `salida/<CODIGO>_etiqueta.png`: **QR** con la URL de reclamo, más el código y la clave impresos (por si el celular no puede escanear). También dibuja el QR en la terminal. Si falla, **descarta** la matera (`DELETE`) para que no quede una sin etiqueta.
4. Genera `salida/<CODIGO>.h`: el `config.h` del firmware (WiFi, servidor, código y token).
5. Guarda `../materas_fabricadas/<CODIGO>.json` para poder probarla con `simulador_esp32.py`.

El diagrama completo (fábrica → reclamo → handshake de la ESP) está en [`docs/FLUJO_FABRICA_Y_CONEXION.md`](../docs/FLUJO_FABRICA_Y_CONEXION.md).

**Qué vincula la ESP con la planta:** el *código* de la matera. El token del firmware y la clave del QR son de ese código. La tarjeta RFID **no** hace falta para vincular: solo identifica la matera dentro de la fábrica (inventario, soporte). El celular no la puede leer (el iPhone no lee MIFARE Classic), por eso el usuario reclama con el QR. **El token del ESP32 nunca va en el QR ni en la tarjeta.**

## Instalación

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
```

En `.env`: `FABRICA_CLAVE` igual a la de `backend/.env`, `ESP_SERVIDOR` con la IP del PC en la red (no `localhost`: para el ESP32 es él mismo) y el WiFi. Para que el teléfono pueda abrir el QR, `FRONT_URL` en `backend/.env` también debe usar la IP del PC.

## Uso

```bash
.venv/bin/python estacion.py --especie potos                    # solo QR, varias seguidas
.venv/bin/python estacion.py --especie potos --una              # una sola
.venv/bin/python estacion.py --especie potos --rfid             # + tarjeta RFID (lector RC522)
.venv/bin/python estacion.py --especie potos --rfid --simular   # + tarjeta RFID simulada
.venv/bin/python estacion.py --identificar                      # acercar tarjetas y ver de qué matera son
```

`--puerto /dev/ttyUSB0` si el lector no se detecta solo.

## Lector RC522 (opcional)

El RC522 es un módulo **SPI**: no se conecta directo al PC. Va a un ESP32 (o Arduino Uno/Nano) que hace de puente USB con el sketch [`firmware/estacion_rfid/estacion_rfid.ino`](../firmware/estacion_rfid/estacion_rfid.ino) (biblioteca **MFRC522** del Library Manager).

| RC522 | ESP32 DevKit | Arduino Uno/Nano |
|---|---|---|
| SDA | GPIO 5 | D10 |
| SCK | GPIO 18 | D13 |
| MOSI | GPIO 23 | D11 |
| MISO | GPIO 19 | D12 |
| IRQ | — | — |
| GND | GND | GND |
| RST | GPIO 22 | D9 |
| 3.3V | 3V3 | 3.3V |

**El RC522 va a 3.3 V, nunca a 5 V.**

Para probar solo el lector: abre el Monitor Serie a 115200. Al arrancar debe decir `LISTO RC522 version=0x92` (o `0x91`/`0x88` en clones); si dice `ERROR RC522 sin respuesta`, revisa los cables. Al acercar una tarjeta sale `UID 04A1B2C3` y al retirarla `RETIRADA`. **Cierra el Monitor Serie antes de correr la estación**, porque los dos no pueden abrir el puerto a la vez.

Si en Linux sale `Permission denied` en `/dev/ttyUSB0`: `sudo usermod -aG uucp $USER` (Arch) o `dialout` (Ubuntu/Debian), y vuelve a iniciar sesión.

## Tests

```bash
.venv/bin/python -m pytest -q tests
```
