from ultralytics import YOLO
import cv2
import mysql.connector

# Connect to MySQL
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Hashtag@1501",
    database="roadwatch"
)

cursor = db.cursor()

# Load trained model
model = YOLO("runs/detect/train-3/weights/best.pt")

# Open video
cap = cv2.VideoCapture("dataset/sample_video.mp4")

while True:
    ret, frame = cap.read()

    if not ret:
        break

    # Run detection
    results = model(frame)

    # Draw detection boxes
    annotated_frame = results[0].plot()

    # Save detections to MySQL
    for box in results[0].boxes:

        confidence = float(box.conf[0])

        query = """
        INSERT INTO detections (object_name, confidence)
        VALUES (%s, %s)
        """

        values = ("pothole", confidence)

        cursor.execute(query, values)
        db.commit()

        print("Detection saved!")

    # Show video
    cv2.imshow("RoadWatch AI", annotated_frame)

    # ESC key to exit
    if cv2.waitKey(25) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()

cursor.close()
=======
from ultralytics import YOLO
import cv2
import mysql.connector

# Connect to MySQL
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Hashtag@1501",
    database="roadwatch"
)

cursor = db.cursor()

# Load trained model
model = YOLO("runs/detect/train-3/weights/best.pt")

# Open video
cap = cv2.VideoCapture("dataset/sample_video.mp4")

while True:
    ret, frame = cap.read()

    if not ret:
        break

    # Run detection
    results = model(frame)

    # Draw detection boxes
    annotated_frame = results[0].plot()

    # Save detections to MySQL
    for box in results[0].boxes:

        confidence = float(box.conf[0])

        query = """
        INSERT INTO detections (object_name, confidence)
        VALUES (%s, %s)
        """

        values = ("pothole", confidence)

        cursor.execute(query, values)
        db.commit()

        print("Detection saved!")

    # Show video
    cv2.imshow("RoadWatch AI", annotated_frame)

    # ESC key to exit
    if cv2.waitKey(25) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()

cursor.close()
>>>>>>> cf7261940bfbbc27e5fcdb27140748a71711bd34
db.close()