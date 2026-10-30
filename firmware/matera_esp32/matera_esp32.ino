/*
 * Firmware de la matera inteligente (ESP32).
 *
 * Hace lo mismo que simulador_esp32.py pero desde la placa real: se conecta al
 * WiFi y cada INTERVALO_MS envía POST /api/dispositivos/<codigo>/lecturas con
 * su token de dispositivo. La fecha la pone el servidor (no hace falta NTP).
 *
 * Por ahora la placa no tiene sensores: los valores se simulan con una deriva
 * suave (la humedad baja y "se riega"). Cuando se conecten los sensores solo
 * cambia leerSensores(); el resto del firmware y el backend quedan igual.
 *
 * LED integrado (GPIO2): parpadeo corto = lectura aceptada (201),
 * tres parpadeos = el servidor la rechazó, encendido fijo = sin WiFi.
 */
#include <WiFi.h>
#include <HTTPClient.h>
#include "config.h"

const int LED = 2;

float humedad = 55, luz = 700, temperatura = 24;

void parpadear(int veces) {
  for (int i = 0; i < veces; i++) {
    digitalWrite(LED, HIGH); delay(120);
    digitalWrite(LED, LOW);  delay(120);
  }
}

void conectarWifi() {
  if (WiFi.status() == WL_CONNECTED) return;
  digitalWrite(LED, HIGH);
  Serial.printf("Conectando a %s", WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_CLAVE);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  digitalWrite(LED, LOW);
  Serial.printf("\nConectado, IP %s\n", WiFi.localIP().toString().c_str());
}

void leerSensores() {
  humedad -= random(2, 12) / 10.0;
  if (humedad < 40) humedad = 62;  // riego
  luz = constrain(luz + random(-60, 61), 300, 1200);
  temperatura = constrain(temperatura + random(-3, 4) / 10.0, 18, 30);
}

void enviarLectura() {
  HTTPClient http;
  String url = String(API_URL) + "/api/dispositivos/" + CODIGO_MATERA + "/lecturas";
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("Authorization", String("Bearer ") + TOKEN_MATERA);

  char cuerpo[160];
  snprintf(cuerpo, sizeof(cuerpo),
           "{\"dispositivo\":\"%s\",\"humedad\":%.1f,\"luz\":%.0f,\"temperatura\":%.1f}",
           CODIGO_MATERA, humedad, luz, temperatura);

  int codigo = http.POST(cuerpo);
  Serial.printf("%s -> %d %s\n", cuerpo, codigo, http.getString().c_str());
  http.end();

  if (codigo == 201) parpadear(1);
  else parpadear(3);
}

void setup() {
  Serial.begin(115200);
  pinMode(LED, OUTPUT);
  randomSeed(esp_random());
  conectarWifi();
}

void loop() {
  conectarWifi();
  leerSensores();
  enviarLectura();
  delay(INTERVALO_MS);
}
