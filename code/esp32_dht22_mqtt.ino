/*
  STEP 3 FIRMWARE — DHT22 sensor + WiFi + MQTT, sent to Mosquitto on the Pi.
  Build and test esp32_dht22_test.ino FIRST. Only move to this file once
  that one prints good readings in the Serial Monitor.

  What it does, every SLEEP_MINUTES:
    1. Reads temperature + humidity from the DHT22
    2. Connects to WiFi
    3. Connects to Mosquitto (running on the Raspberry Pi) and publishes one
       JSON message
    4. Goes back to deep sleep

  Libraries needed (Arduino IDE -> Library Manager):
    - "DHT sensor library" by Adafruit (+ "Adafruit Unified Sensor")
    - "PubSubClient" by Nick O'Leary

  Wiring (same as the test sketch):
    DHT22 VCC  -> 3V3
    DHT22 DATA -> GPIO 15   (+ 10k resistor from DATA to 3V3)
    DHT22 GND  -> GND
*/

#include <WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>

// =====================  SETTINGS - EDIT THESE  =====================
const char* WIFI_SSID = "YOUR_WIFI_NAME";
const char* WIFI_PASS = "YOUR_WIFI_PASSWORD";

const char* MQTT_HOST = "192.168.1.50";     // the Raspberry Pi's LAN IP (Step 2 told you how to find it)
const uint16_t MQTT_PORT = 1883;

const char* DEVICE_ID = "esp32-room1";
const char* TOPIC      = "home/room1/temperature";   // full JSON

#define SLEEP_MINUTES 30   // set to 1 while testing, change to 30 once everything works
#define DHT_PIN       15
#define DHT_TYPE      DHT22
// ===================================================================

WiFiClient netClient;
PubSubClient mqtt(netClient);
DHT dht(DHT_PIN, DHT_TYPE);

bool readSensor(float &temp, float &hum) {
  dht.begin();
  delay(2000);                 // DHT22 needs ~2s after power-up before its first read
  for (int attempt = 0; attempt < 3; attempt++) {
    hum  = dht.readHumidity();
    temp = dht.readTemperature();
    if (!isnan(hum) && !isnan(temp)) return true;   // good read
    delay(1000);
  }
  return false;   // failed 3 times in a row
}

bool connectWifi(uint32_t timeoutMs = 20000) {
  WiFi.mode(WIFI_STA);              // "station" mode: join a network, don't create one
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  uint32_t start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < timeoutMs) {
    delay(250);
  }
  bool ok = WiFi.status() == WL_CONNECTED;
  Serial.println(ok ? "WiFi connected" : "WiFi FAILED");
  return ok;
}

void publishReading(float temp, float hum) {
  mqtt.setServer(MQTT_HOST, MQTT_PORT);

  // a unique client name, so two boards never collide on the broker
  String clientId = String(DEVICE_ID) + "-" + String((uint32_t)ESP.getEfuseMac(), HEX);

  for (int i = 0; i < 3 && !mqtt.connected(); i++) {
    if (!mqtt.connect(clientId.c_str())) {
      Serial.printf("MQTT connect failed, state=%d\n", mqtt.state());
      delay(2000);
    }
  }
  if (!mqtt.connected()) {
    Serial.println("Could not reach the broker - reading is lost this cycle");
    return;
  }

  char payload[160];
  snprintf(payload, sizeof(payload),
           "{\"device\":\"%s\",\"temp_c\":%.2f,\"humidity\":%.1f,\"rssi\":%d}",
           DEVICE_ID, temp, hum, WiFi.RSSI());

  // retain = true: the broker remembers this as the last value,
  // so a phone that connects later sees it immediately
  mqtt.publish(TOPIC, payload, true);
  mqtt.loop();            // lets the library actually push the bytes out
  Serial.println(payload);

  delay(200);              // small pause so the packet has time to leave before we disconnect
  mqtt.disconnect();
}

void goToSleep() {
  WiFi.disconnect(true);
  WiFi.mode(WIFI_OFF);
  Serial.println("Sleeping...");
  Serial.flush();          // make sure the print above actually reaches the Serial Monitor
  esp_sleep_enable_timer_wakeup((uint64_t)SLEEP_MINUTES * 60ULL * 1000000ULL);
  esp_deep_sleep_start();  // board switches off almost everything until the timer fires
}

void setup() {
  Serial.begin(115200);

  float temp, hum;
  bool gotReading = readSensor(temp, hum);

  if (gotReading) {
    Serial.printf("Temp: %.1f C  Humidity: %.1f %%\n", temp, hum);
    if (connectWifi()) {
      publishReading(temp, hum);
    }
  } else {
    Serial.println("Sensor read failed, skipping this cycle");
  }

  goToSleep();
}

void loop() {}   // never reached: setup() ends in deep sleep
