/*
  Fingerprint Sensor - Standalone Test Sketch

  Wiring:
    Red    -> 5V
    Black  -> GND
    Yellow -> GPIO 16  (try swapping with White if "not found")
    White  -> GPIO 17  (try swapping with Yellow if "not found")
    Green  -> not connected
    Blue   -> not connected

  Requires library: Adafruit Fingerprint Sensor Library
  (Tools -> Manage Libraries -> search "Adafruit Fingerprint")
*/

#include <Adafruit_Fingerprint.h>

#define FINGERPRINT_RX 16   // connects to sensor's TX
#define FINGERPRINT_TX 17   // connects to sensor's RX

HardwareSerial fingerSerial(2); // UART2
Adafruit_Fingerprint finger = Adafruit_Fingerprint(&fingerSerial);

void setup() {
  Serial.begin(115200);
  delay(100);
  Serial.println("Initializing fingerprint sensor...");

  fingerSerial.begin(57600, SERIAL_8N1, FINGERPRINT_RX, FINGERPRINT_TX);
  // If this doesn't work, try changing 57600 to 9600 above and re-upload

  delay(100);

  if (finger.verifyPassword()) {
    Serial.println("Fingerprint sensor found and ready.");
  } else {
    Serial.println("Fingerprint sensor NOT found. Check wiring/baud rate.");
  }

  Serial.println("Type 's' and press Enter to scan a finger.");
}

void loop() {
  if (Serial.available()) {
    char cmd = Serial.read();
    if (cmd == 's' || cmd == 'S') {
      Serial.println("Place finger on sensor...");

      int p = -1;
      unsigned long startTime = millis();
      while (p != FINGERPRINT_OK) {
        p = finger.getImage();
        if (millis() - startTime > 10000) {
          Serial.println("Timed out waiting for finger.");
          return;
        }
      }

      Serial.println("Image captured successfully!");
    }
  }
}
