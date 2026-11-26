// Copia este archivo como config.h y llena los datos (o usa el que genera la
// estación de fábrica: fabrica/salida/<CODIGO>.h).
// config.h no se sube al repo: contiene la clave del WiFi y el token de la matera.
#pragma once

#define WIFI_SSID      "nombre-de-tu-wifi"
#define WIFI_CLAVE     "clave-de-tu-wifi"

// IP del computador que corre el backend (flask --host 0.0.0.0), en la misma red.
// No uses localhost: para el ESP32, localhost es él mismo.
#define SERVIDOR_HOST    "192.168.1.50"
#define SERVIDOR_PUERTO  5000

// Salen de materas_fabricadas/<CODIGO>.json (flask fabricar-matera) o de la estación de fábrica.
#define CODIGO_MATERA  "MAT-ESP32"
#define TOKEN_MATERA   "dev_reemplaza_con_el_token_de_la_fabrica"
