/*
 * Puente USB del lector RFID RC522 para la estación de fábrica (fabrica/estacion.py --rfid).
 *
 * El RC522 es un módulo SPI: no se conecta directo al PC. Esta placa (ESP32 o
 * Arduino Uno/Nano) lo lee y manda por el cable USB, a 115200 baudios:
 *
 *   LISTO RC522 version=0x92    al arrancar, si el módulo responde
 *   ERROR RC522 sin respuesta   si no responde (revisa el cableado)
 *   UID 04A1B2C3                una vez, al acercar una tarjeta
 *   RETIRADA                    al retirarla
 *
 * Si el PC manda "?", repite la línea LISTO/ERROR (para placas que no se
 * reinician al abrir el puerto).
 *
 * Biblioteca: "MFRC522" de GithubCommunity (miguelbalboa), desde el Library Manager.
 *
 * Cableado (el RC522 va a 3.3V, NUNCA a 5V):
 *
 *   RC522   ESP32 DevKit   Arduino Uno/Nano
 *   SDA     GPIO 5         D10
 *   SCK     GPIO 18        D13
 *   MOSI    GPIO 23        D11
 *   MISO    GPIO 19        D12
 *   IRQ     (sin conectar) (sin conectar)
 *   GND     GND            GND
 *   RST     GPIO 22        D9
 *   3.3V    3V3            3.3V
 */
#include <SPI.h>
#include <MFRC522.h>

#if defined(ESP32)
  #define PIN_SS   5
  #define PIN_RST  22
#else
  #define PIN_SS   10
  #define PIN_RST  9
#endif

// Cuánto tiempo sin ver la tarjeta para darla por retirada.
#define RETIRO_MS 600

MFRC522 rfid(PIN_SS, PIN_RST);
String uidActual = "";
unsigned long vistaPorUltimaVez = 0;

String uidHex(const MFRC522::Uid &uid) {
  String texto = "";
  for (byte i = 0; i < uid.size; i++) {
    if (uid.uidByte[i] < 0x10) texto += "0";
    texto += String(uid.uidByte[i], HEX);
  }
  texto.toUpperCase();
  return texto;
}

void saludar() {
  byte version = rfid.PCD_ReadRegister(MFRC522::VersionReg);
  if (version == 0x00 || version == 0xFF) {
    Serial.println("ERROR RC522 sin respuesta (revisa SDA, SCK, MOSI, MISO, RST y 3.3V)");
  } else {
    Serial.print("LISTO RC522 version=0x");
    Serial.println(version, HEX);
  }
}

bool tarjetaPresente() {
  // PICC_IsNewCardPresent solo detecta tarjetas "dormidas"; para saber si la
  // misma sigue ahí se la despierta con WUPA cada vez.
  byte atqa[2];
  byte largo = sizeof(atqa);
  if (rfid.PICC_WakeupA(atqa, &largo) != MFRC522::STATUS_OK &&
      !rfid.PICC_IsNewCardPresent()) {
    return false;
  }
  return rfid.PICC_ReadCardSerial();
}

void setup() {
  Serial.begin(115200);
  while (!Serial) { }          // Leonardo/Micro: esperar el USB
  SPI.begin();
  rfid.PCD_Init();
  delay(50);
  saludar();
}

void loop() {
  if (Serial.available()) {
    if (Serial.read() == '?') saludar();
  }

  if (tarjetaPresente()) {
    String uid = uidHex(rfid.uid);
    rfid.PICC_HaltA();
    vistaPorUltimaVez = millis();
    if (uid != uidActual) {    // se avisa una sola vez por tarjeta
      uidActual = uid;
      Serial.print("UID ");
      Serial.println(uid);
    }
  } else if (uidActual != "" && millis() - vistaPorUltimaVez > RETIRO_MS) {
    uidActual = "";
    Serial.println("RETIRADA");
  }
  delay(50);
}
