import time
import ssl
import paho.mqtt.client as mqtt

# =========================================================
# Local Mosquitto Settings
# =========================================================
LOCAL_BROKER = "127.0.0.1"
LOCAL_PORT = 1883

# =========================================================
# AWS IoT Core Settings
# =========================================================
AWS_ENDPOINT = "a20vyaga26egib-ats.iot.us-east-1.amazonaws.com"
AWS_PORT = 8883

ROOT_CA = "certs/AmazonRootCA1.pem"
DEVICE_CERT = "certs/device-certificate.pem.crt"
PRIVATE_KEY = "certs/private.pem.key"

# =========================================================
# Topics
# Local -> AWS

# =========================================================
LOCAL_TO_AWS_TOPICS = [
    "smartfarm/all/data",
    "smartfarm/ai/report",
    "smartfarm/ai/analysis",
    "smartfarm/guard/status",
    "smartfarm/guard/alert",
    "smartfarm/gate/access",
    "smartfarm/gate/name"
]

# =========================================================
# AWS -> Local
# أوامر التحكم فقط
# علشان تقدري تتحكمي من AWS IoT Test Client
# =========================================================
AWS_TO_LOCAL_TOPICS = [
    "smartfarm/control/gate",
    "smartfarm/control/buzzer"
]


# =========================================================
# Helper: Create MQTT Client compatible with old/new paho
# =========================================================
def create_client(client_id):
    try:
        return mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=client_id
        )
    except Exception:
        return mqtt.Client(client_id=client_id)


# =========================================================
# Clients
# =========================================================
local_client = create_client("SmartFarm_Local_Bridge")
aws_client = create_client("SmartFarm_AWS_Bridge")


# =========================================================
# Local MQTT Callbacks
# =========================================================
def on_local_connect(client, userdata, flags, rc, *extra):
    if rc == 0:
        print("[LOCAL] Connected to Mosquitto")

        for topic in LOCAL_TO_AWS_TOPICS:
            client.subscribe(topic)
            print(f"[LOCAL] Subscribed: {topic}")

    else:
        print("[LOCAL] Connection failed, rc =", rc)


def on_local_message(client, userdata, msg):
    topic = msg.topic
    payload = msg.payload.decode(errors="ignore")

    print(f"[LOCAL -> AWS] {topic}: {payload}")

    if aws_client.is_connected():
        aws_client.publish(topic, payload)
    else:
        print("[AWS] Not connected, message not forwarded")


# =========================================================
# AWS MQTT Callbacks
# =========================================================
def on_aws_connect(client, userdata, flags, rc, *extra):
    if rc == 0:
        print("[AWS] Connected to AWS IoT Core")

        for topic in AWS_TO_LOCAL_TOPICS:
            client.subscribe(topic)
            print(f"[AWS] Subscribed: {topic}")

    else:
        print("[AWS] Connection failed, rc =", rc)


def on_aws_message(client, userdata, msg):
    topic = msg.topic
    payload = msg.payload.decode(errors="ignore")

    print(f"[AWS -> LOCAL] {topic}: {payload}")

    if local_client.is_connected():
        local_client.publish(topic, payload)
    else:
        print("[LOCAL] Not connected, command not forwarded")


# =========================================================
# Setup Local Client
# =========================================================
local_client.on_connect = on_local_connect
local_client.on_message = on_local_message


# =========================================================
# Setup AWS Client with TLS Certificates
# =========================================================
aws_client.on_connect = on_aws_connect
aws_client.on_message = on_aws_message

aws_client.tls_set(
    ca_certs=ROOT_CA,
    certfile=DEVICE_CERT,
    keyfile=PRIVATE_KEY,
    cert_reqs=ssl.CERT_REQUIRED,
    tls_version=ssl.PROTOCOL_TLS_CLIENT
)


# =========================================================
# Main
# =========================================================
def main():
    print("========================================")
    print("Smart Farm MQTT Bridge")
    print("Local Mosquitto <-> AWS IoT Core")
    print("========================================")

    print("[LOCAL] Connecting to Mosquitto...")
    local_client.connect(LOCAL_BROKER, LOCAL_PORT, 60)

    print("[AWS] Connecting to AWS IoT Core...")
    aws_client.connect(AWS_ENDPOINT, AWS_PORT, 60)

    local_client.loop_start()
    aws_client.loop_start()

    print("Bridge is running...")
    print("Local -> AWS topics:")
    for t in LOCAL_TO_AWS_TOPICS:
        print("  ", t)

    print("AWS -> Local control topics:")
    for t in AWS_TO_LOCAL_TOPICS:
        print("  ", t)

    print("----------------------------------------")
    print("Press Ctrl + C to stop")
    print("----------------------------------------")

    try:
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nStopping bridge...")

        local_client.loop_stop()
        aws_client.loop_stop()

        local_client.disconnect()
        aws_client.disconnect()

        print("Bridge stopped.")


if __name__ == "__main__":
    main()