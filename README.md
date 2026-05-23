# Smart Farm Monitoring and Security System

## Project Overview

Smart Farm Monitoring and Security System is an IoT-based project built using ESP32, sensors, actuators, MQTT communication, and a dashboard/AI system. The project monitors farm environmental conditions, controls irrigation status, checks feed level, detects guard alerts, and controls a smart gate using face recognition results.

The ESP32 collects sensor readings and publishes them to an MQTT broker. The dashboard or AI system can also send control commands back to the ESP32, such as opening/closing the gate or activating the buzzer.

---

## Features

- Monitor temperature and humidity using DHT11 sensor.
- Detect gas/smoke level using gas sensor.
- Measure soil moisture level.
- Control pump status using an LED indicator.
- Detect water level using a digital water sensor.
- Measure feed level using ultrasonic sensor.
- Open and close gate using servo motor.
- Auto-close gate after a fixed duration.
- Activate buzzer alerts for security warnings.
- Receive guard sleeping/awake alert through MQTT.
- Receive face recognition access result through MQTT.
- Publish all readings as JSON to MQTT.
- Support dashboard commands for gate and buzzer control.

---

## Hardware Components

- ESP32 Development Board
- DHT11 Temperature and Humidity Sensor
- Soil Moisture Sensor
- Gas Sensor
- Water Level Sensor
- Ultrasonic Sensor HC-SR04
- Servo Motor
- Buzzer
- LED for Pump Simulation
- Jumper Wires
- Breadboard

---

## Software and Tools

- Arduino IDE
- Mosquitto MQTT Broker
- MQTT Client / Dashboard
- ESP32 Board Package
- Required Arduino Libraries:
  - WiFi.h
  - PubSubClient.h
  - DHT.h
  - ESP32Servo.h

---

## IoT Architecture Layers

### 1. Perception Layer
This layer contains the sensors and actuators that interact with the real world.

Examples:
- DHT11
- Soil Moisture Sensor
- Gas Sensor
- Water Sensor
- Ultrasonic Sensor
- Servo Motor
- Buzzer

### 2. Network Layer
This layer is responsible for sending and receiving data.

Used technologies:
- WiFi
- MQTT Protocol
- Mosquitto Broker

### 3. Processing Layer
This layer processes data and makes decisions.

Examples:
- AI face recognition system
- Guard sleeping detection system
- Dashboard logic
- Backend/MQTT processing

### 4. Application Layer
This is the user-facing layer.

Examples:
- Dashboard
- Farm monitoring interface
- Gate control panel
- Alerts display

---

## Pin Configuration

| Component | ESP32 Pin |
|---|---|
| DHT11 | GPIO 27 |
| Soil Moisture Sensor | GPIO 35 |
| Water Sensor | GPIO 22 |
| Gas Sensor | GPIO 34 |
| Ultrasonic TRIG | GPIO 26 |
| Ultrasonic ECHO | GPIO 32 |
| Pump LED | GPIO 2 |
| Servo Motor | GPIO 33 |
| Buzzer | GPIO 23 |

---

## MQTT Configuration

```cpp
const char* mqtt_server = "192.168.1.7";
```

The ESP32 connects to the MQTT broker using port:

```cpp
1883
```

Make sure the MQTT broker IP matches your computer/server IP address.

---

## MQTT Topics

### Published Topic

The ESP32 publishes all farm data to:

```text
smartfarm/all/data
```

Example JSON message:

```json
{
  "temperature": 28.50,
  "humidity": 60.00,
  "gas": 1200,
  "soil": 3100,
  "water": 1,
  "distance": 12.50,
  "feed_percent": 76,
  "feed_status": "ok",
  "need_food": 0,
  "guard_alert": 0,
  "gate_access": "granted",
  "gate_name": "Ahmed",
  "door_open": 1,
  "pump": 1
}
```

### Subscribed Topics

| Topic | Description | Expected Message |
|---|---|---|
| `smartfarm/guard/alert` | Receives guard status | `1` = sleeping, `0` = awake |
| `smartfarm/gate/access` | Receives face recognition result | `granted` or `denied` |
| `smartfarm/gate/name` | Receives recognized person name | Any name |
| `smartfarm/control/gate` | Dashboard gate control | `open` or `close` |
| `smartfarm/control/buzzer` | Dashboard buzzer control | `short3` or `long` |

---

## System Logic

### Soil Moisture and Pump

If the soil moisture value is greater than the dry threshold, the system considers the soil dry and turns ON the pump LED.

```cpp
if (soilValue > SOIL_DRY_THRESHOLD) {
    pumpStatus = 1;
} else {
    pumpStatus = 0;
}
```

### Feed Level

The ultrasonic sensor measures the distance between the sensor and the feed surface.

- Small distance means the feed container is full.
- Large distance means the feed container is empty.

The system maps the distance to a percentage from 0% to 100%.

### Gate Access

- If access is `granted`, the servo opens the gate.
- If access is `denied`, the gate remains closed and the buzzer gives a long alert.
- The gate automatically closes after 5 seconds.

### Guard Alert

- If the guard alert message is `1`, the system considers the guard sleeping and activates the buzzer 3 times.
- If the message is `0`, the guard is awake and the buzzer is turned off.

---

## How to Run the Project

### 1. Install Required Libraries

In Arduino IDE, install:

- PubSubClient
- DHT sensor library
- ESP32Servo

### 2. Connect the Hardware

Connect all sensors and actuators according to the pin configuration table.

### 3. Start MQTT Broker

If you are using Mosquitto on Windows, run:

```bash
mosquitto -c mosquitto.conf -v
```

Make sure the broker is listening on port 1883.

### 4. Update WiFi and MQTT Settings

Edit these lines in the code:

```cpp
const char* ssid = "YOUR_WIFI_NAME";
const char* password = "YOUR_WIFI_PASSWORD";
const char* mqtt_server = "YOUR_BROKER_IP";
```

### 5. Upload Code to ESP32

Select the correct ESP32 board and COM port in Arduino IDE, then upload the code.

### 6. Monitor Serial Output

Open Serial Monitor at:

```text
9600 baud
```

You should see WiFi connection, MQTT connection, sensor readings, and published JSON data.

---

## Testing MQTT

To subscribe to all farm messages:

```bash
mosquitto_sub -h 127.0.0.1 -t smartfarm/#
```

To send a guard sleeping alert:

```bash
mosquitto_pub -h 127.0.0.1 -t smartfarm/guard/alert -m "1"
```

To send a guard awake alert:

```bash
mosquitto_pub -h 127.0.0.1 -t smartfarm/guard/alert -m "0"
```

To open the gate from dashboard/MQTT:

```bash
mosquitto_pub -h 127.0.0.1 -t smartfarm/control/gate -m "open"
```

To close the gate:

```bash
mosquitto_pub -h 127.0.0.1 -t smartfarm/control/gate -m "close"
```

To activate buzzer 3 times:

```bash
mosquitto_pub -h 127.0.0.1 -t smartfarm/control/buzzer -m "short3"
```

To activate long buzzer alert:

```bash
mosquitto_pub -h 127.0.0.1 -t smartfarm/control/buzzer -m "long"
```

---

## Suggested Repository Structure

```text
Smart-Farm-IoT/
│
├── ESP32_Code/
│   └── smart_farm_esp32.ino
│
├── Dashboard/
│   └── dashboard files
│
├── AI_System/
│   └── face_recognition_or_guard_detection files
│
├── README.md
└── images/
    └── project screenshots
```

---

## Future Improvements

- Add real water pump instead of LED simulation.
- Add mobile application for remote monitoring.
- Store sensor readings in a database.
- Add real-time charts to the dashboard.
- Add notification system for low feed, gas danger, or guard sleeping.
- Improve security using MQTT username and password.
- Add cloud integration using AWS IoT Core.

---

## Project Summary

This project demonstrates a complete IoT smart farm system using ESP32 and MQTT. The system collects data from different sensors, controls actuators, communicates with a dashboard, and integrates with AI-based security features such as face recognition and guard alert detection.
