/*
 * Firmware de la matera inteligente (ESP32) — versión WebSocket.
 *
 * Al encender:
 *   1. Se conecta al WiFi de config.h.
 *   2. Abre UN WebSocket con el backend (ws://SERVIDOR_HOST:SERVIDOR_PUERTO/ws/dispositivos)
 *      y lo deja abierto. Se presenta con su código y su token de fábrica.
 *   3. Cada `intervalo_s` segundos (lo dice el backend en la bienvenida) envía una lectura.
 *   4. Cumple las órdenes que lleguen por el mismo socket: parpadear, reportar, regar.
 * Si se cae el WiFi o el servidor, reintenta solo cada 5 s.
 *
 * Por qué ya no hay delay() en loop(): webSocket.loop() tiene que correr
 * siempre para responder los ping del servidor. Si la placa se queda dormida
 * en un delay(10000), el servidor no recibe el pong y la da por desconectada.
 * Por eso el tiempo entre lecturas se cuenta con millis().
 *
 * Bibliotecas (Arduino IDE > Administrar bibliotecas):
 *   - "WebSockets" de Markus Sattler (links2004)   >= 2.4
 *   - "ArduinoJson" de Benoit Blanchon             >= 7.0
 * Placa: "ESP32 Dev Module" (paquete esp32 de Espressif).
 *
 * Por ahora la placa no tiene sensores: los valores se simulan con una deriva
 * suave (la humedad baja y "se riega"). Cuando se conecten los sensores solo
 * cambia leerSensores(); el resto del firmware y el backend quedan igual.
 *
 * LED integrado (GPIO2): parpadeo corto = lectura aceptada, tres parpadeos =
 * el servidor la rechazó, encendido fijo = sin WiFi o sin servidor,
 * cinco parpadeos = orden "parpadear" (para encontrar la matera).
 */
#include <WiFi.h>
#include <WebSocketsClient.h>
#include <ArduinoJson.h>
#include "config.h"

#define FIRMWARE_VERSION "2.0.0"

const int LED = 2;
// Cuando haya bomba, conectarla (con relé o transistor) a este pin.
const int PIN_BOMBA = LED;

WebSocketsClient webSocket;
bool conectada = false;
unsigned long intervaloMs = 10000;   // el backend lo cambia en la bienvenida
unsigned long ultimaLectura = 0;
unsigned long riegoHasta = 0;

float humedad = 55, luz = 700, temperatura = 24;

void parpadear(int veces) {
  for (int i = 0; i < veces; i++) {
    digitalWrite(LED, HIGH); delay(120);
    digitalWrite(LED, LOW);  delay(120);
  }
}

void leerSensores() {
  humedad -= random(2, 12) / 10.0;
  if (humedad < 40) humedad = 62;  // riego
  luz = constrain(luz + random(-60, 61), 300, 1200);
  temperatura = constrain(temperatura + random(-3, 4) / 10.0, 18, 30);
}

void enviarJson(JsonDocument& doc) {
  String texto;
  serializeJson(doc, texto);
  webSocket.sendTXT(texto);
}

void enviarSaludo() {
  JsonDocument doc;
  doc["tipo"] = "hola";
  doc["codigo"] = CODIGO_MATERA;
  doc["token"] = TOKEN_MATERA;
  doc["firmware"] = FIRMWARE_VERSION;
  enviarJson(doc);
}

void enviarLectura() {
  leerSensores();
  JsonDocument doc;
  doc["tipo"] = "lectura";   // la fecha la pone el servidor (no hace falta NTP)
  doc["humedad"] = humedad;
  doc["luz"] = luz;
  doc["temperatura"] = temperatura;
  enviarJson(doc);
  ultimaLectura = millis();
  Serial.printf("[lectura] humedad=%.1f luz=%.1f temperatura=%.1f\n", humedad, luz, temperatura);
}

void confirmarOrden(const char* id) {
  JsonDocument doc;
  doc["tipo"] = "orden_ok";
  doc["id"] = id;
  enviarJson(doc);
}

void cumplirOrden(JsonDocument& mensaje) {
  const char* orden = mensaje["orden"] | "";
  const char* id = mensaje["id"] | "";
  Serial.printf("[orden] %s (%s)\n", orden, id);

  if (strcmp(orden, "parpadear") == 0) {
    parpadear(5);
  } else if (strcmp(orden, "reportar") == 0) {
    enviarLectura();
  } else if (strcmp(orden, "regar") == 0) {
    int segundos = mensaje["parametros"]["segundos"] | 0;
    // Sin bloquear el loop: la bomba se apaga sola en loop() al cumplirse el tiempo.
    digitalWrite(PIN_BOMBA, HIGH);
    riegoHasta = millis() + (unsigned long)segundos * 1000UL;
  } else {
    Serial.println("[orden] desconocida, se ignora");
    return;
  }
  confirmarOrden(id);
}

void alRecibirMensaje(uint8_t* datos, size_t largo) {
  JsonDocument mensaje;
  if (deserializeJson(mensaje, datos, largo)) {
    Serial.println("[ws] el mensaje no es JSON");
    return;
  }
  const char* tipo = mensaje["tipo"] | "";

  if (strcmp(tipo, "bienvenida") == 0) {
    conectada = true;
    digitalWrite(LED, LOW);
    intervaloMs = (mensaje["intervalo_s"] | 10) * 1000UL;
    Serial.printf("[ws] conectada como %s (%s), lectura cada %lus\n",
                  (const char*)(mensaje["codigo"] | "?"),
                  (mensaje["reclamada"] | false) ? "reclamada" : "sin dueño: falta tocar el sticker",
                  intervaloMs / 1000);
    enviarLectura();                         // primera lectura de inmediato
  } else if (strcmp(tipo, "lectura_ok") == 0) {
    parpadear(1);
  } else if (strcmp(tipo, "orden") == 0) {
    cumplirOrden(mensaje);
  } else if (strcmp(tipo, "error") == 0) {
    Serial.printf("[ws] error del servidor: %s - %s\n",
                  (const char*)(mensaje["error"] | ""), (const char*)(mensaje["mensaje"] | ""));
    parpadear(3);
  }
}

void alEventoWebSocket(WStype_t tipo, uint8_t* datos, size_t largo) {
  switch (tipo) {
    case WStype_CONNECTED:
      Serial.println("[ws] conectado al servidor, enviando saludo");
      enviarSaludo();
      break;
    case WStype_DISCONNECTED:
      if (conectada) Serial.println("[ws] desconectado, reintentando...");
      conectada = false;
      digitalWrite(LED, HIGH);
      break;
    case WStype_TEXT:
      alRecibirMensaje(datos, largo);
      break;
    default:
      break;
  }
}

void conectarWifi() {
  digitalWrite(LED, HIGH);
  Serial.printf("[wifi] conectando a %s", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_CLAVE);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.printf("\n[wifi] conectado, IP %s\n", WiFi.localIP().toString().c_str());
}

void setup() {
  Serial.begin(115200);
  delay(200);
  pinMode(LED, OUTPUT);
  pinMode(PIN_BOMBA, OUTPUT);
  randomSeed(esp_random());
  Serial.printf("\nMatera %s - firmware %s\n", CODIGO_MATERA, FIRMWARE_VERSION);

  WiFi.setAutoReconnect(true);
  conectarWifi();

  webSocket.begin(SERVIDOR_HOST, SERVIDOR_PUERTO, "/ws/dispositivos");
  webSocket.onEvent(alEventoWebSocket);
  webSocket.setReconnectInterval(5000);        // reintenta cada 5 s si se cae
  webSocket.enableHeartbeat(15000, 3000, 2);   // la placa también detecta un servidor caído
}

void loop() {
  webSocket.loop();   // responde los ping del servidor: no bloquear nunca el loop

  if (riegoHasta && (long)(millis() - riegoHasta) >= 0) {
    digitalWrite(PIN_BOMBA, LOW);
    riegoHasta = 0;
    Serial.println("[riego] terminado");
  }

  if (conectada && millis() - ultimaLectura >= intervaloMs) {
    enviarLectura();
  }
}
