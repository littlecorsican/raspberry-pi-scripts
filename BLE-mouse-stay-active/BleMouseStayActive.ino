#include <BleMouse.h>

#define LED_PIN 2
#define BLINK_INTERVAL 300  // ms

BleMouse bleMouse;
bool wasConnected = false;

unsigned long lastBlink = 0;
bool ledState = false;

void setup() {
  Serial.begin(115200);
  delay(1000);

  pinMode(LED_PIN, OUTPUT);

  Serial.println("Starting BLE Mouse...");
  bleMouse.begin();

  randomSeed(esp_random());
}

void loop() {
  if (bleMouse.isConnected()) {
    // BLE connected → LED solid ON
    digitalWrite(LED_PIN, HIGH);
    wasConnected = true;

    int dx = random(-25, 25);
    int dy = random(-25, 25);

    Serial.print("[BLE CONNECTED] Moving mouse: dx=");
    Serial.print(dx);
    Serial.print(", dy=");
    Serial.println(dy);

    bleMouse.move(dx, dy);
    delay(6000);

  } else {
    Serial.println("[BLE NOT CONNECTED]");

    // Flash LED when not connected
    unsigned long now = millis();
    if (now - lastBlink >= BLINK_INTERVAL) {
      lastBlink = now;
      ledState = !ledState;
      digitalWrite(LED_PIN, ledState);
    }

    // Restart BLE advertising if it was connected before
    if (wasConnected) {
      Serial.println("Restarting BLE advertising...");
      bleMouse.end();
      delay(500);
      bleMouse.begin();
      wasConnected = false;
    }

    delay(2000);
  }
}
