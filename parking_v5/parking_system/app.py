# -*- coding: utf-8 -*-
from flask import Flask, send_from_directory, request, jsonify, Response
import json
import serial
import cv2
from RPLCD.i2c import CharLCD
from time import sleep
import threading
import os
from datetime import datetime
# -------------------------------
# Configurations
# -------------------------------
SERIAL_PORT = "/dev/serial0"
SERIAL_BAUD = 9600
MAX_SLOTS = 40
LOG_FILE = "logs.json"
# -------------------------------
# Global State
# -------------------------------
serial_conn = None
cars_in_parking = set()
# -------------------------------
# LCD Setup
# -------------------------------
lcd = CharLCD('PCF8574', 0x27)
lcd.clear()
def show_home_screen():
    lcd.clear()
    lcd.write_string("Scanning...")
    lcd.cursor_pos = (1, 0)
    lcd.write_string(f"Slots: {len(cars_in_parking)}/{MAX_SLOTS}")
show_home_screen()
# -------------------------------
# Flask App Setup
# -------------------------------
app = Flask(__name__, static_folder=".")
# -------------------------------
# Serial Handler
# -------------------------------
def get_serial_connection():
    global serial_conn
    if serial_conn is not None:
        return serial_conn
    try:
        serial_conn = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=1)
        print(f"[OK] Serial connection established on {SERIAL_PORT}")
    except Exception as e:
        print(f"[ERROR] Could not open serial port {SERIAL_PORT}: {e}")
        serial_conn = None
    return serial_conn
# -------------------------------
# Log Handler
# -------------------------------
def append_log(plate, action):
    log_entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "plate": plate,
        "action": "entering" if action == 1 else "leaving"
    }
    if not os.path.isfile(LOG_FILE):
        with open(LOG_FILE, "w") as f:
            json.dump([log_entry], f, indent=4)
    else:
        with open(LOG_FILE, "r+") as f:
            try:
                data = json.load(f)
                data.append(log_entry)
                f.seek(0)
                json.dump(data, f, indent=4)
            except json.JSONDecodeError:
                f.seek(0)
                json.dump([log_entry], f, indent=4)
# -------------------------------
# Camera Feed Generator
# -------------------------------
def gen_frames():
    cam = cv2.VideoCapture(0)
    if not cam.isOpened():
        print("[ERROR] Camera not available")
        return
    try:
        while True:
            success, frame = cam.read()
            if not success:
                print("[ERROR] Failed to read frame")
                break
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    finally:
        cam.release()
# -------------------------------
# Web Routes
# -------------------------------
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')
@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')
@app.route('/serial_event', methods=['POST'])
def serial_event():
    data = request.get_json(force=True, silent=True)
    if not isinstance(data, dict):
        return jsonify({'status': 'error', 'message': 'Invalid JSON'}), 400
    plate = data.get('plate', 'UNKNOWN')
    action = data.get('action')  # 1 = Entering, 0 = Leaving
 # Update parking set
    if action == 1:
        if len(cars_in_parking) < MAX_SLOTS:
            cars_in_parking.add(plate)
    elif action == 0:
        cars_in_parking.discard(plate)
    # Send to serial
    ser = get_serial_connection()
    if ser:
        try:
            ser.write((json.dumps(data) + '\n').encode('utf-8'))
            print(f"[>] Sent to serial: {json.dumps(data)}")
        except Exception as e:
            print(f"[ERROR] Serial write failed: {e}")
    # Display result on LCD
    lcd.clear()
    lcd.write_string("Car Entering" if action == 1 else "Car Leaving")
    lcd.cursor_pos = (1, 0)
    lcd.write_string(f"Plate: {plate[:10]}")
    # Log the event
    append_log(plate, action)
    # Return to home screen after 3 seconds
    threading.Timer(3.0, show_home_screen).start()
    return jsonify({'status': 'ok'})
# -------------------------------
# Logs Endpoint (Descending Order)
# -------------------------------
@app.route('/logs', methods=['GET'])
def get_logs():
    if not os.path.isfile(LOG_FILE):
        return jsonify([])
    try:
        with open(LOG_FILE, "r") as f:
            logs = json.load(f)
        sorted_logs = sorted(logs, key=lambda x: x["timestamp"], reverse=True)
        return jsonify(sorted_logs)
    except Exception as e:
        return jsonify({"error": f"Failed to read logs: {str(e)}"}), 500
# -------------------------------
# Run App
# -------------------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
