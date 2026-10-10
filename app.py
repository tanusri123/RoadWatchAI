from flask import Flask, render_template, request, redirect, session, Response
import os
import cv2
import random
import mysql.connector
from ultralytics import YOLO

app = Flask(__name__)

app.secret_key = "pavevision_secret"

UPLOAD_FOLDER = "uploads"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Hashtag@1501",
    database="roadwatch"
)

cursor = db.cursor()

model = YOLO("runs/detect/train-3/weights/best.pt")


@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        query = """
        SELECT * FROM users
        WHERE username=%s AND password=%s
        """

        cursor.execute(query, (username, password))

        user = cursor.fetchone()

        if user:

            session['user'] = username

            query = """
            INSERT INTO login_history
            (username, login_time)
            VALUES (%s, NOW())
            """

            cursor.execute(query, (username,))
            db.commit()

            return redirect('/')

        else:
            return "Invalid Username or Password"

    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        query = """
        INSERT INTO users
        (username, password)
        VALUES (%s, %s)
        """

        cursor.execute(query, (username, password))
        db.commit()

        return redirect('/login')

    return render_template('signup.html')


@app.route('/logout')
def logout():

    session.pop('user', None)

    return redirect('/login')


@app.route('/')
def home():

    if 'user' not in session:
        return redirect('/login')

    cursor.execute("SELECT COUNT(*) FROM detections")
    pothole_count = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM detections WHERE severity='Minor'"
    )
    minor_count = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM detections WHERE severity='Medium'"
    )
    medium_count = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM detections WHERE severity='Severe'"
    )
    severe_count = cursor.fetchone()[0]

    query = """
    SELECT severity, latitude, longitude, status, detected_time
    FROM detections
    ORDER BY id DESC
    LIMIT 5
    """

    cursor.execute(query)

    recent_detections = cursor.fetchall()

    return render_template(
        'index.html',
        pothole_count=pothole_count,
        minor_count=minor_count,
        medium_count=medium_count,
        severe_count=severe_count,
        recent_detections=recent_detections,
        username=session['user']
    )


@app.route('/upload', methods=['POST'])
def upload():

    if 'user' not in session:
        return redirect('/login')

    if 'file' not in request.files:
        return "No file uploaded"

    file = request.files['file']

    if file.filename == '':
        return "No selected file"

    filepath = os.path.join(
        app.config['UPLOAD_FOLDER'],
        file.filename
    )

    file.save(filepath)

    extension = filepath.split('.')[-1].lower()

    query = """
    INSERT INTO uploads
    (filename, upload_time)
    VALUES (%s, NOW())
    """

    cursor.execute(query, (file.filename,))
    db.commit()

    if extension in ['jpg', 'jpeg', 'png']:

        image = cv2.imread(filepath)

        results = model(image)

        for box in results[0].boxes:

            confidence = float(box.conf[0])

            latitude = round(
                random.uniform(12.90, 13.10),
                5
            )

            longitude = round(
                random.uniform(77.50, 77.70),
                5
            )

            x1, y1, x2, y2 = box.xyxy[0]

            area = (x2 - x1) * (y2 - y1)

            if area < 5000:
                severity = "Minor"

            elif area < 15000:
                severity = "Medium"

            else:
                severity = "Severe"

            query = """
            INSERT INTO detections
            (
                object_name,
                confidence,
                latitude,
                longitude,
                severity,
                status
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """

            values = (
                "pothole",
                confidence,
                latitude,
                longitude,
                severity,
                "Pending"
            )

            cursor.execute(query, values)
            db.commit()

    return redirect('/')


@app.route('/live')
def live():

    if 'user' not in session:
        return redirect('/login')

    return render_template(
        'live.html',
        username=session['user']
    )


def generate_frames():

    cap = cv2.VideoCapture(0)

    while True:

        success, frame = cap.read()

        if not success:
            break

        results = model(frame)

        for result in results:

            boxes = result.boxes

            for box in boxes:

                confidence = float(box.conf[0])

                if confidence < 0.40:
                    continue

                x1, y1, x2, y2 = map(
                    int,
                    box.xyxy[0]
                )

                width = x2 - x1
                height = y2 - y1

                area = width * height

                if area < 5000:

                    severity = "Minor"
                    color = (0, 255, 0)

                elif area < 15000:

                    severity = "Medium"
                    color = (0, 165, 255)

                else:

                    severity = "Severe"
                    color = (0, 0, 255)

                cv2.rectangle(
                    frame,
                    (x1, y1),
                    (x2, y2),
                    color,
                    3
                )

                label = f"{severity} ({confidence:.2f})"

                cv2.putText(
                    frame,
                    label,
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    color,
                    2
                )

        ret, buffer = cv2.imencode('.jpg', frame)

        frame = buffer.tobytes()

        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n'
            + frame +
            b'\r\n'
        )

    cap.release()


@app.route('/video_feed')
def video_feed():

    return Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@app.route('/uploads')
def uploads():

    if 'user' not in session:
        return redirect('/login')

    query = """
    SELECT *
    FROM uploads
    ORDER BY id DESC
    """

    cursor.execute(query)

    uploads_data = cursor.fetchall()

    return render_template(
        'uploads.html',
        uploads=uploads_data,
        username=session['user']
    )


@app.route('/history')
def history():

    if 'user' not in session:
        return redirect('/login')

    severity_filter = request.args.get('severity')

    if severity_filter:

        query = """
        SELECT *
        FROM detections
        WHERE LOWER(severity)=LOWER(%s)
        ORDER BY id DESC
        """

        cursor.execute(query, (severity_filter,))

    else:

        query = """
        SELECT *
        FROM detections
        ORDER BY id DESC
        """

        cursor.execute(query)

    detections = cursor.fetchall()

    return render_template(
        'history.html',
        detections=detections,
        username=session['user'],
        severity_filter=severity_filter
    )


@app.route('/gps')
def gps():

    if 'user' not in session:
        return redirect('/login')

    severity_filter = request.args.get('severity')

    if severity_filter:

        query = """
        SELECT *
        FROM detections
        WHERE LOWER(severity)=LOWER(%s)
        ORDER BY id DESC
        """

        cursor.execute(query, (severity_filter,))

    else:

        query = """
        SELECT *
        FROM detections
        ORDER BY id DESC
        """

        cursor.execute(query)

    detections = cursor.fetchall()

    return render_template(
        'gps.html',
        detections=detections,
        username=session['user'],
        severity_filter=severity_filter
    )


@app.route('/analytics')
def analytics():

    if 'user' not in session:
        return redirect('/login')

    cursor.execute("SELECT COUNT(*) FROM detections")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT AVG(confidence) FROM detections")
    avg_confidence = cursor.fetchone()[0]

    if avg_confidence is None:
        avg_confidence = 0

    avg_confidence = round(avg_confidence * 100, 2)

    return render_template(
        'analytics.html',
        total=total,
        avg_confidence=avg_confidence,
        username=session['user']
    )


if __name__ == '__main__':
    app.run(debug=True)