import json
import paho.mqtt.client as mqtt

# ================= MQTT SETTINGS =================
BROKER_IP = "127.0.0.1"
BROKER_PORT = 1883

INPUT_TOPIC = "smartfarm/all/data"
OUTPUT_ANALYSIS_TOPIC = "smartfarm/ai/analysis"
OUTPUT_REPORT_TOPIC = "smartfarm/ai/report"


# ================= AI ANALYSIS FUNCTIONS =================

def analyze_temperature(temp):
    if temp is None:
        return "unknown", "Temperature reading is missing."

    if temp < 18:
        return "cold", "Temperature is low. Animals may need warmer conditions."
    elif 18 <= temp <= 32:
        return "normal", "Temperature is suitable for the barn."
    else:
        return "high", "Temperature is high. Ventilation or cooling may be needed."


def analyze_humidity(humidity):
    if humidity is None:
        return "unknown", "Humidity reading is missing."

    if humidity < 30:
        return "low", "Humidity is low. Air may be too dry."
    elif 30 <= humidity <= 70:
        return "normal", "Humidity level is acceptable."
    else:
        return "high", "Humidity is high. Ventilation may be needed."


def analyze_gas(gas):
    if gas is None:
        return "unknown", "Gas reading is missing."

    if gas < 1000:
        return "safe", "Gas level is normal."
    elif 1000 <= gas < 2000:
        return "warning", "Gas level is increasing. Monitor the barn."
    else:
        return "danger", "Gas level is high. Immediate ventilation is recommended."


def analyze_soil(soil):
    if soil is None:
        return "unknown", "Soil reading is missing."

    if soil > 3000:
        return "dry", "Soil is dry. Irrigation may be needed."
    elif 1500 <= soil <= 3000:
        return "medium", "Soil moisture is moderate."
    else:
        return "wet", "Soil is wet enough. Irrigation is not needed."


def analyze_water(water):
    if water is None:
        return "unknown", "Water sensor reading is missing."

    if water == 1:
        return "available", "Water is detected."
    else:
        return "not_available", "No water detected."


def analyze_feed(feed_percent, feed_status, need_food, distance):
    if feed_status == "unknown" or feed_percent is None or feed_percent == -1:
        return "unknown", "Feed level reading is not available."

    if need_food == 1:
        return "low", "Feed level is low. Animals need food."

    if feed_percent >= 60:
        return "good", "Feed level is good."
    elif 30 < feed_percent < 60:
        return "medium", "Feed level is moderate."
    else:
        return "low", "Feed level is low. Refill may be needed."


def analyze_guard(guard_alert):
    if guard_alert is None:
        return "unknown", "Guard status is missing."

    if guard_alert == 1:
        return "sleeping", "Guard appears to be sleeping. Alert is required."
    else:
        return "awake", "Guard is awake or normal."


def analyze_gate(gate_access, door_open):
    if gate_access == "granted":
        if door_open == 1:
            return "open", "Gate is open for an authorized person."
        return "closed_after_access", "Gate access was granted and the door is now closed."

    if gate_access == "denied":
        return "denied", "Access denied. Unknown person detected."

    if gate_access == "manual_open":
        if door_open == 1:
            return "manual_open", "Gate was opened manually from the dashboard."
        return "manual_closed_after_open", "Gate was opened manually and is now closed."

    if gate_access == "manual_close":
        return "manual_close", "Gate was closed manually from the dashboard."

    return "unknown", "Gate status is unknown."


def overall_decision(results):
    attention_statuses = [
        "danger",
        "sleeping",
        "denied",
        "low",
        "not_available",
        "dry",
        "high",
        "unknown"
    ]

    critical = []

    for key, value in results.items():
        if value["status"] in attention_statuses:
            critical.append(key)

    if len(critical) == 0:
        return "NORMAL", "All monitored farm conditions are acceptable."

    return "ATTENTION_NEEDED", "Some farm conditions need attention: " + ", ".join(critical)


def generate_text_report(analysis_json):
    overall_status = analysis_json["overall_status"]
    details = analysis_json["details"]

    problems = []
    stable = []

    for sensor_name, result in details.items():
        status = result["status"]

        if status in ["danger", "sleeping", "denied", "low", "not_available", "dry", "high", "unknown"]:
            problems.append(f"{sensor_name} is {status}")
        else:
            stable.append(f"{sensor_name} is {status}")

    if overall_status == "NORMAL":
        return "Farm status is normal. All monitored conditions are acceptable."

    report = "Farm needs attention. "

    if problems:
        report += "Main issues: " + ", ".join(problems) + ". "

    if stable:
        report += "Stable parts: " + ", ".join(stable[:4]) + "."

    return report


def analyze_farm_data(data):
    temp = data.get("temperature")
    humidity = data.get("humidity")
    gas = data.get("gas")
    soil = data.get("soil")
    water = data.get("water")

    distance = data.get("distance")
    feed_percent = data.get("feed_percent")
    feed_status = data.get("feed_status")
    need_food = data.get("need_food")

    guard_alert = data.get("guard_alert")
    gate_access = data.get("gate_access")
    door_open = data.get("door_open")

    temp_status, temp_msg = analyze_temperature(temp)
    hum_status, hum_msg = analyze_humidity(humidity)
    gas_status, gas_msg = analyze_gas(gas)
    soil_status, soil_msg = analyze_soil(soil)
    water_status, water_msg = analyze_water(water)
    feed_status_result, feed_msg = analyze_feed(feed_percent, feed_status, need_food, distance)
    guard_status, guard_msg = analyze_guard(guard_alert)
    gate_status, gate_msg = analyze_gate(gate_access, door_open)

    results = {
        "temperature": {"status": temp_status, "message": temp_msg},
        "humidity": {"status": hum_status, "message": hum_msg},
        "gas": {"status": gas_status, "message": gas_msg},
        "soil": {"status": soil_status, "message": soil_msg},
        "water": {"status": water_status, "message": water_msg},
        "feed": {"status": feed_status_result, "message": feed_msg},
        "guard": {"status": guard_status, "message": guard_msg},
        "gate": {"status": gate_status, "message": gate_msg},
    }

    overall_status, overall_msg = overall_decision(results)

    analysis_json = {
        "overall_status": overall_status,
        "overall_message": overall_msg,
        "details": results
    }

    text_report = generate_text_report(analysis_json)
    analysis_json["text_report"] = text_report

    return analysis_json


# ================= MQTT CALLBACKS =================

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT Broker")
        client.subscribe(INPUT_TOPIC)
        print(f"Subscribed to input topic: {INPUT_TOPIC}")
        print(f"Publishing JSON analysis to: {OUTPUT_ANALYSIS_TOPIC}")
        print(f"Publishing text report to: {OUTPUT_REPORT_TOPIC}")
        print("--------------------------------------")
    else:
        print("Failed to connect, return code:", rc)


def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode()
        data = json.loads(payload)

        analysis_json = analyze_farm_data(data)
        text_report = analysis_json["text_report"]

        print("\n========== AI FARM ANALYSIS ==========")
        print("Raw Data:", data)
        print("--------------------------------------")
        print("Overall Status:", analysis_json["overall_status"])
        print("Decision:", analysis_json["overall_message"])
        print("Text Report:", text_report)
        print("--------------------------------------")

        for sensor_name, result in analysis_json["details"].items():
            print(f"{sensor_name.upper()}: {result['status']} -> {result['message']}")

        print("======================================")

        # Publish detailed JSON analysis
        analysis_payload = json.dumps(analysis_json)
        client.publish(OUTPUT_ANALYSIS_TOPIC, analysis_payload)

        # Publish text report for dashboard
        client.publish(OUTPUT_REPORT_TOPIC, text_report)

        print("AI Analysis Published to MQTT")
        print("AI Text Report Published to MQTT")

    except json.JSONDecodeError:
        print("Error: Received message is not valid JSON")
        print("Message:", msg.payload.decode())

    except Exception as e:
        print("Error while analyzing data:", e)


# ================= MAIN =================

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(BROKER_IP, BROKER_PORT, 60)
client.loop_forever()