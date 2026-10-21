/*
  STEP 1 TEST SKETCH — sensor only, no WiFi, no MQTT.
  Purpose: prove the DHT22 is wired correctly and readable before
  adding any networking complexity on top.

  Wiring:
    DHT22 pin 1 (VCC)  -> ESP32 3V3
    DHT22 pin 2 (DATA) -> ESP32 GPIO 15   (+ 10k resistor from DATA to 3V3)
    DHT22 pin 3         -> not connected
    DHT22 pin 4 (GND)  -> ESP32 GND

  Library needed (Arduino IDE -> Library Manager):
    "DHT sensor library" by Adafruit  (installing it also offers
    "Adafruit Unified Sensor" as a dependency — accept that too)
*/

#include <DHT.h>

#define DHT_PIN  15
#define DHT_TYPE DHT22

DHT dht(DHT_PIN, DHT_TYPE);

void setup() {
  Serial.begin(115200);   // opens the serial link so Serial Monitor can show text
  delay(1000);             // give the sensor a moment to power up
  dht.begin();              // starts the DHT library
}

void loop() {
  delay(2000);              // DHT22 can only be read about once every 2 seconds

  float humidity    = dht.readHumidity();
  float temperature = dht.readTemperature();   // Celsius by default

  if (isnan(humidity) || isnan(temperature)) {
    // isnan() = "is not a number" -> the read failed (bad wiring, bad timing, dead sensor)
    Serial.println("Failed to read from DHT22 sensor");
    return;   // skip the rest of this loop, try again in 2s
  }

  Serial.print("Temperature: ");
  Serial.print(temperature);
  Serial.print(" C   Humidity: ");
  Serial.print(humidity);
  Serial.println(" %");
}
