#include <WiFi.h>
#include <PubSubClient.h>
#include "DHT.h"
#include <ESP32Servo.h>

// ================= WiFi =================
const char* ssid = "iotlab";
const char* password = "hostiotlab";

// ================= MQTT =================
const char* mqtt_server = "192.168.137.1";

WiFiClient espClient;
PubSubClient client(espClient);

// ================= DHT11 =================
#define DHTPIN 27
#define DHTTYPE DHT11
DHT dht(DHTPIN, DHTTYPE);

// ================= Sensors =================
#define SOIL_PIN 35
#define WATER_PIN 22
#define GAS_PIN 34

#define TRIG_PIN 26
#define ECHO_PIN 32

// ================= Pump LED =================
#define PUMP_LED_PIN 2
int SOIL_DRY_THRESHOLD = 3000;
int pumpStatus = 0;

// ================= Feed Level =================
float FULL_DISTANCE = 5.0;
float EMPTY_DISTANCE = 35.0;

int FEED_LOW_THRESHOLD = 30;
int feedPercent = -1;
int needFood = 0;
String feedStatus = "unknown";

// ================= Servo Gate =================
#define SERVO_PIN 33
Servo gateServo;

#define DOOR_CLOSED_ANGLE 0
#define DOOR_OPEN_ANGLE 90

bool doorIsOpen = false;
unsigned long doorOpenTime = 0;
const unsigned long DOOR_OPEN_DURATION = 5000;

// ================= Buzzer =================
#define BUZZER_PIN 23

// ================= Guard Alert =================
int guardAlert = 0;

// ================= Gate Access =================
String gateAccess = "denied";
String gateName = "Unknown";

// ================= Publish Timing =================
unsigned long lastPublishTime = 0;
const unsigned long PUBLISH_INTERVAL = 3000;

// ================= Unknown Person Buzzer Cooldown =================
unsigned long lastUnknownBuzzTime = 0;
const unsigned long UNKNOWN_BUZZ_COOLDOWN = 7000;

void setup() {
  Serial.begin(9600);

  dht.begin();

  pinMode(GAS_PIN, INPUT);
  pinMode(SOIL_PIN, INPUT);
  pinMode(WATER_PIN, INPUT);

  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  pinMode(PUMP_LED_PIN, OUTPUT);
  digitalWrite(PUMP_LED_PIN, LOW);

  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);

  gateServo.attach(SERVO_PIN);
  closeGate();

  connectWiFi();

  client.setServer(mqtt_server, 1883);
  client.setCallback(callback);

  Serial.println("Smart Farm System Started");
}

void loop() {
  if (!client.connected()) {
    reconnectMQTT();
  }

  client.loop();

  checkDoorAutoClose();

  unsigned long now = millis();

  if (now - lastPublishTime >= PUBLISH_INTERVAL) {
    lastPublishTime = now;

    float temp = dht.readTemperature();
    float hum = dht.readHumidity();

    int gasValue = analogRead(GAS_PIN);
    int soilValue = analogRead(SOIL_PIN);
    int waterValue = digitalRead(WATER_PIN);

    float distance = readUltrasonic();

    if (soilValue > SOIL_DRY_THRESHOLD) {
      digitalWrite(PUMP_LED_PIN, HIGH);
      pumpStatus = 1;
      Serial.println("Soil is dry -> Pump LED ON");
    } else {
      digitalWrite(PUMP_LED_PIN, LOW);
      pumpStatus = 0;
      Serial.println("Soil is wet -> Pump LED OFF");
    }

    calculateFeedLevel(distance);

    Serial.print("Temp: ");
    Serial.print(temp);
    Serial.print(" C | Humidity: ");
    Serial.print(hum);
    Serial.print(" % | Gas: ");
    Serial.print(gasValue);
    Serial.print(" | Soil: ");
    Serial.print(soilValue);
    Serial.print(" | Pump: ");
    Serial.print(pumpStatus);
    Serial.print(" | Water: ");
    Serial.print(waterValue);

    if (distance == -1) {
      Serial.print(" | Distance: No reading");
    } else {
      Serial.print(" | Distance: ");
      Serial.print(distance);
      Serial.print(" cm");
    }

    Serial.print(" | Feed: ");
    Serial.print(feedPercent);
    Serial.print("% | Feed Status: ");
    Serial.print(feedStatus);
    Serial.print(" | Need Food: ");
    Serial.print(needFood);
    Serial.print(" | Guard Alert: ");
    Serial.print(guardAlert);
    Serial.print(" | Gate: ");
    Serial.print(gateAccess);
    Serial.print(" | Name: ");
    Serial.print(gateName);
    Serial.print(" | Door Open: ");
    Serial.println(doorIsOpen ? 1 : 0);

    publishJsonReadings(
      temp,
      hum,
      gasValue,
      soilValue,
      waterValue,
      distance,
      feedPercent,
      feedStatus,
      needFood,
      guardAlert,
      gateAccess,
      gateName,
      doorIsOpen,
      pumpStatus
    );
  }
}

// ================= WiFi =================
void connectWiFi() {
  Serial.println("Connecting to WiFi...");

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.println("WiFi Connected");
  Serial.print("ESP32 IP: ");
  Serial.println(WiFi.localIP());
}

// ================= MQTT =================
void reconnectMQTT() {
  while (!client.connected()) {
    Serial.println("Connecting to MQTT...");

    if (client.connect("ESP32_SmartFarm_Client")) {
      Serial.println("MQTT Connected");

      client.subscribe("smartfarm/guard/alert");
      client.subscribe("smartfarm/gate/access");
      client.subscribe("smartfarm/gate/name");

      client.subscribe("smartfarm/control/gate");
      client.subscribe("smartfarm/control/buzzer");

      Serial.println("Subscribed to guard, gate and dashboard control topics");

    } else {
      Serial.print("MQTT Failed, rc=");
      Serial.println(client.state());
      delay(3000);
    }
  }
}

void callback(char* topic, byte* payload, unsigned int length) {
  String message = "";

  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }

  String topicStr = String(topic);

  Serial.print("Message arrived [");
  Serial.print(topicStr);
  Serial.print("]: ");
  Serial.println(message);

  if (topicStr == "smartfarm/guard/alert") {
    if (message == "1") {
      guardAlert = 1;
      Serial.println("Guard Status: Sleeping");
      buzzerAlert3Times();
    } else if (message == "0") {
      guardAlert = 0;
      Serial.println("Guard Status: Awake");
      digitalWrite(BUZZER_PIN, LOW);
    }
  }

  if (topicStr == "smartfarm/gate/access") {
    gateAccess = message;

    if (message == "granted") {
      Serial.println("Access Granted - Opening Gate");
      openGate();
    } else if (message == "denied") {
      Serial.println("Access Denied - Unknown Person");
      closeGate();

      unsigned long now = millis();
      if (now - lastUnknownBuzzTime >= UNKNOWN_BUZZ_COOLDOWN) {
        lastUnknownBuzzTime = now;
        buzzerLongAlert();
      }
    }
  }

  if (topicStr == "smartfarm/gate/name") {
    gateName = message;
  }

  if (topicStr == "smartfarm/control/gate") {
    if (message == "open") {
      Serial.println("Dashboard Command: Open Gate");
      gateAccess = "manual_open";
      gateName = "Dashboard";
      openGate();
    } else if (message == "close") {
      Serial.println("Dashboard Command: Close Gate");
      gateAccess = "manual_close";
      gateName = "Dashboard";
      closeGate();
    }
  }

  if (topicStr == "smartfarm/control/buzzer") {
    if (message == "short3") {
      Serial.println("Dashboard Command: Buzzer 3 Beeps");
      buzzerAlert3Times();
    } else if (message == "long") {
      Serial.println("Dashboard Command: Long Buzzer Alert");
      buzzerLongAlert();
    }
  }
}

// ================= Feed Level Logic =================
void calculateFeedLevel(float distance) {
  if (distance == -1) {
    feedPercent = -1;
    needFood = 0;
    feedStatus = "unknown";
    return;
  }

  feedPercent = map(distance, EMPTY_DISTANCE, FULL_DISTANCE, 0, 100);

  if (feedPercent > 100) feedPercent = 100;
  if (feedPercent < 0) feedPercent = 0;

  if (feedPercent <= FEED_LOW_THRESHOLD) {
    needFood = 1;
    feedStatus = "need_food";
  } else {
    needFood = 0;
    feedStatus = "ok";
  }
}

// ================= Gate Control =================
void openGate() {
  gateServo.write(DOOR_OPEN_ANGLE);
  doorIsOpen = true;
  doorOpenTime = millis();
  Serial.println("Gate Opened");
}

void closeGate() {
  gateServo.write(DOOR_CLOSED_ANGLE);
  doorIsOpen = false;
  Serial.println("Gate Closed");
}

void checkDoorAutoClose() {
  if (doorIsOpen && millis() - doorOpenTime >= DOOR_OPEN_DURATION) {
    Serial.println("Auto Closing Gate");
    closeGate();
  }
}

// ================= Buzzer Alerts =================
void buzzerAlert3Times() {
  for (int i = 0; i < 3; i++) {
    digitalWrite(BUZZER_PIN, HIGH);
    delay(300);

    digitalWrite(BUZZER_PIN, LOW);
    delay(300);
  }

  digitalWrite(BUZZER_PIN, LOW);
}

void buzzerLongAlert() {
  digitalWrite(BUZZER_PIN, HIGH);
  delay(1500);

  digitalWrite(BUZZER_PIN, LOW);
}

// ================= Ultrasonic =================
float readUltrasonic() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);

  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);

  digitalWrite(TRIG_PIN, LOW);

  long duration = pulseIn(ECHO_PIN, HIGH, 30000);

  if (duration == 0) {
    return -1;
  }

  float distance = duration * 0.034 / 2;

  if (distance < 2 || distance > 80) {
    return -1;
  }

  return distance;
}

// ================= Publish JSON =================
void publishJsonReadings(
  float temp,
  float hum,
  int gasValue,
  int soilValue,
  int waterValue,
  float distance,
  int feedPercent,
  String feedStatus,
  int needFood,
  int guardAlert,
  String gateAccess,
  String gateName,
  bool doorIsOpen,
  int pumpStatus
) {
  char jsonData[650];

  if (distance == -1) {
    snprintf(
      jsonData,
      sizeof(jsonData),
      "{\"temperature\":%.2f,\"humidity\":%.2f,\"gas\":%d,\"soil\":%d,\"water\":%d,\"distance\":-1,\"feed_percent\":%d,\"feed_status\":\"%s\",\"need_food\":%d,\"guard_alert\":%d,\"gate_access\":\"%s\",\"gate_name\":\"%s\",\"door_open\":%d,\"pump\":%d}",
      temp,
      hum,
      gasValue,
      soilValue,
      waterValue,
      feedPercent,
      feedStatus.c_str(),
      needFood,
      guardAlert,
      gateAccess.c_str(),
      gateName.c_str(),
      doorIsOpen ? 1 : 0,
      pumpStatus
    );
  } else {
    snprintf(
      jsonData,
      sizeof(jsonData),
      "{\"temperature\":%.2f,\"humidity\":%.2f,\"gas\":%d,\"soil\":%d,\"water\":%d,\"distance\":%.2f,\"feed_percent\":%d,\"feed_status\":\"%s\",\"need_food\":%d,\"guard_alert\":%d,\"gate_access\":\"%s\",\"gate_name\":\"%s\",\"door_open\":%d,\"pump\":%d}",
      temp,
      hum,
      gasValue,
      soilValue,
      waterValue,
      distance,
      feedPercent,
      feedStatus.c_str(),
      needFood,
      guardAlert,
      gateAccess.c_str(),
      gateName.c_str(),
      doorIsOpen ? 1 : 0,
      pumpStatus
    );
  }

  client.publish("smartfarm/all/data", jsonData);

  Serial.print("JSON Sent: ");
  Serial.println(jsonData);
}