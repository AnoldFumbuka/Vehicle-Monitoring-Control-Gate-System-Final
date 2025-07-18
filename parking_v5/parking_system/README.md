# Parking Management System

This folder contains a simple Flask application for a parking management system that uses OCR to read license plates. The web interface allows image uploads, live camera scanning, or manual capture using a webcam. Detected plates are cross-checked against a small demo database and results are sent over the Raspberry Pi serial port.

## Requirements

- Python 3
- Flask
- OpenCV (`opencv-python`)
- `pyserial`
- A webcam (USB or PiCamera configured as `/dev/video0`)
- Optional: serial device connected to `/dev/serial0`

If you see `[ERROR] Camera not available` in the logs, make sure a webcam is
connected and accessible as `/dev/video0`.

Install dependencies using the provided `requirements.txt` file:
```bash
pip install -r requirements.txt
```

## Usage
Run the server from within this directory:
```bash
python app.py
```
Then open `http://<raspberrypi-ip>:5000` in a browser on the same network.

The page provides options for image upload, live scanning, and capturing frames for analysis. Plate data is sent to the serial port for integration with external hardware such as gates or indicators.
