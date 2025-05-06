#!/usr/bin/env python3
import os, sys, socket, subprocess, threading, signal

# ————— CONFIGURATION —————
HOST = ''            
PORT = 4002          # update PI_PORT in AudioPlayer.ino to 4001

BASE = os.path.dirname(os.path.abspath(__file__))
YOLO_SCRIPT = os.path.join(BASE, "yolo_detect.py")
YOLO_CMD = [
    sys.executable, YOLO_SCRIPT,
    "--model", "best_ncnn_model",
    "--source", "picamera0",
    "--resolution", "1280x720"
]

esp_conn  = None
yolo_proc = None

def start_yolo():
    global yolo_proc
    if yolo_proc is None or yolo_proc.poll() is not None:
        yolo_proc = subprocess.Popen(
            YOLO_CMD,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        threading.Thread(target=monitor_yolo, daemon=True).start()
        print("✅ YOLO process started")

def stop_yolo():
    global yolo_proc
    if yolo_proc and yolo_proc.poll() is None:
        print("🛑 Stopping YOLO")
        yolo_proc.send_signal(signal.SIGINT)
        yolo_proc.wait()
    yolo_proc = None

def monitor_yolo():
    for line in yolo_proc.stdout:
        print("YOLO |", line, end='')
        if line.startswith("DETECT:"):
            esp_conn.sendall((line.strip() + "\n").encode())
            print(f"→ Sent to ESP32: {line.strip()}")

def main():
    global esp_conn
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(1)
    print(f"🔌 Detect server listening on port {PORT}…")

    while True:
        esp_conn, addr = server.accept()
        print("✅ ESP32 connected from", addr)
        start_yolo()
        try:
            while True:
                # No incoming data expected; just detect disconnects
                data = esp_conn.recv(1024)
                if not data:
                    print("⚠ ESP32 disconnected")
                    break
            stop_yolo()
            esp_conn.close()
        except KeyboardInterrupt:
            break

    server.close()

if __name__ == "__main__":
    main()
