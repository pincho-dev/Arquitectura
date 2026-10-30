// Copia este archivo como config.h y llena los datos.
// config.h no se sube al repo: contiene la clave del WiFi y el token de la matera.
#pragma once

#define WIFI_SSID      "nombre-de-tu-wifi"
#define WIFI_CLAVE     "clave-de-tu-wifi"

// IP del computador que corre el backend (flask --host 0.0.0.0), en la misma red.
#define API_URL        "http://192.168.1.12:5000"

// Sale de materas_fabricadas/<CODIGO>.json (comando fabricar-matera).
#define CODIGO_MATERA  "MAT-XXXX"
#define TOKEN_MATERA   "dev_..."

// Cada cuánto se envía una lectura.
#define INTERVALO_MS   10000
