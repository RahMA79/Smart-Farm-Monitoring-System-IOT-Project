import cv2
import mediapipe as mp
import numpy as np
import time
import os
import paho.mqtt.client as mqtt

from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# ================= MQTT SETTINGS =================
BROKER_IP = "127.0.0.1"   # لأن كود الكاميرا شغال على نفس اللابتوب اللي عليه Mosquitto
BROKER_PORT = 1883

STATUS_TOPIC = "smartfarm/guard/status"
ALERT_TOPIC = "smartfarm/guard/alert"

mqtt_client = mqtt.Client()
mqtt_client.connect(BROKER_IP, BROKER_PORT, 60)
mqtt_client.loop_start()

# ================= FACE LANDMARKER =================
model_path = os.path.join(os.path.dirname(__file__), "face_landmarker.task")

base_options = python.BaseOptions(model_asset_path=model_path)

options = vision.FaceLandmarkerOptions(
    base_options=base_options,
    running_mode=vision.RunningMode.VIDEO,
    num_faces=1
)

landmarker = vision.FaceLandmarker.create_from_options(options)

# ================= FUNCTIONS =================
def difference(p1, p2):
    return np.linalg.norm(np.array(p1) - np.array(p2))


def calculate_EAR(eye_points):
    p1, p2, p3, p4, p5, p6 = eye_points

    vertical1 = difference(p2, p6)
    vertical2 = difference(p3, p5)
    horizontal = difference(p1, p4)

    ear = (vertical1 + vertical2) / (2.0 * horizontal)
    return ear


# ================= EYE POINTS =================
LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]

# ================= CAMERA =================
cap = cv2.VideoCapture(0)

frame_timestamp_ms = 0
closed_frames = 0

last_sent_status = ""

while True:
    ret, frame = cap.read()

    if not ret:
        print("Failed to read from camera")
        break

    frame = cv2.flip(frame, 1)

    h, w, channels = frame.shape

    image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    mp_image = mp.Image(
        image_format=mp.ImageFormat.SRGB,
        data=image_rgb
    )

    results = landmarker.detect_for_video(mp_image, frame_timestamp_ms)
    frame_timestamp_ms += 33

    status = "No Guard Detected"
    color = (255, 255, 255)
    alert_value = "0"

    if results.face_landmarks:
        for face in results.face_landmarks:

            left_eye = []
            right_eye = []

            for idx in LEFT_EYE:
                lm = face[idx]
                left_eye.append((lm.x * w, lm.y * h))

            for idx in RIGHT_EYE:
                lm = face[idx]
                right_eye.append((lm.x * w, lm.y * h))

            left_ear = calculate_EAR(left_eye)
            right_ear = calculate_EAR(right_eye)
            ear = (left_ear + right_ear) / 2.0

            for (x, y) in left_eye + right_eye:
                cv2.circle(frame, (int(x), int(y)), 2, (0, 255, 0), -1)

            # لو العين مقفولة
            if ear < 0.18:
                closed_frames += 1
            else:
                closed_frames = 0

            # لو العين فضلت مقفولة عدد فريمات كبير
            if closed_frames > 15:
                status = "Guard is Sleeping!"
                color = (0, 0, 255)
                alert_value = "1"
            else:
                status = "Guard is Awake"
                color = (0, 255, 0)
                alert_value = "0"

            cv2.putText(frame, f"EAR: {ear:.2f}", (30, 100),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    else:
        closed_frames = 0
        alert_value = "0"

    # ابعت MQTT بس لما الحالة تتغير
    if status != last_sent_status:
        mqtt_client.publish(STATUS_TOPIC, status)
        mqtt_client.publish(ALERT_TOPIC, alert_value)

        print("MQTT Sent:", status, "| Alert:", alert_value)

        last_sent_status = status

    cv2.putText(frame, status, (30, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1, color, 3)

    cv2.imshow("Guard Monitor", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
mqtt_client.loop_stop()
mqtt_client.disconnect()