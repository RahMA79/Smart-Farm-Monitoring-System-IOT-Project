from flask import Flask, render_template, jsonify, request
import paho.mqtt.client as mqtt
import json
import threading

app = Flask(__name__)

# ================= MQTT SETTINGS =================
BROKER_IP = "127.0.0.1"
BROKER_PORT = 1883

FARM_DATA_TOPIC = "smartfarm/all/data"
AI_REPORT_TOPIC = "smartfarm/ai/report"

CONTROL_GATE_TOPIC = "smartfarm/control/gate"
CONTROL_BUZZER_TOPIC = "smartfarm/control/buzzer"

# ================= GLOBAL DATA =================
latest_data = {
    "temperature": "--",
    "humidity": "--",
    "gas": "--",
    "soil": "--",
    "water": "--",
    "distance": "--",
    "feed_percent": "--",
    "feed_status": "--",
    "need_food": "--",
    "guard_alert": "--",
    "gate_access": "--",
    "gate_name": "--",
    "door_open": "--",
    "pump": "--"
}

latest_ai_report = "Waiting for AI report..."

mqtt_client = mqtt.Client()
mqtt_connected = False


# ================= MQTT CALLBACKS =================
def on_connect(client, userdata, flags, rc):
    global mqtt_connected

    if rc == 0:
        mqtt_connected = True
        print("Connected to Mosquitto MQTT Broker")

        client.subscribe(FARM_DATA_TOPIC)
        client.subscribe(AI_REPORT_TOPIC)

        print(f"Subscribed to: {FARM_DATA_TOPIC}")
        print(f"Subscribed to: {AI_REPORT_TOPIC}")
    else:
        mqtt_connected = False
        print("Failed to connect to MQTT Broker. Code:", rc)


def on_message(client, userdata, msg):
    global latest_data, latest_ai_report

    topic = msg.topic
    payload = msg.payload.decode()

    try:
        if topic == FARM_DATA_TOPIC:
            data = json.loads(payload)
            latest_data.update(data)
            print("Farm Data:", data)

        elif topic == AI_REPORT_TOPIC:
            latest_ai_report = payload
            print("AI Report:", latest_ai_report)

    except Exception as e:
        print("Error reading MQTT message:", e)


def start_mqtt():
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message

    mqtt_client.connect(BROKER_IP, BROKER_PORT, 60)
    mqtt_client.loop_forever()


# ================= FLASK ROUTES =================
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/data")
def api_data():
    return jsonify({
        "farm": latest_data,
        "ai_report": latest_ai_report,
        "mqtt_connected": mqtt_connected
    })


@app.route("/api/control", methods=["POST"])
def api_control():
    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "message": "No JSON received"
        }), 400

    target = data.get("target")
    action = data.get("action")

    if target == "gate":
        if action not in ["open", "close"]:
            return jsonify({
                "success": False,
                "message": "Invalid gate action"
            }), 400

        mqtt_client.publish(CONTROL_GATE_TOPIC, action)
        print(f"Control sent: {CONTROL_GATE_TOPIC} -> {action}")

        return jsonify({
            "success": True,
            "message": f"Gate command sent: {action}"
        })

    if target == "buzzer":
        if action not in ["short3", "long"]:
            return jsonify({
                "success": False,
                "message": "Invalid buzzer action"
            }), 400

        mqtt_client.publish(CONTROL_BUZZER_TOPIC, action)
        print(f"Control sent: {CONTROL_BUZZER_TOPIC} -> {action}")

        return jsonify({
            "success": True,
            "message": f"Buzzer command sent: {action}"
        })

    return jsonify({
        "success": False,
        "message": "Unknown target"
    }), 400


# ================= MAIN =================
if __name__ == "__main__":
    mqtt_thread = threading.Thread(target=start_mqtt)
    mqtt_thread.daemon = True
    mqtt_thread.start()

    print("Starting Smart Farm Dashboard...")
    print("Open: http://127.0.0.1:5050")

    app.run(host="0.0.0.0", port=5050, debug=True, use_reloader=False)