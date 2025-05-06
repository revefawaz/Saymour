#!/usr/bin/env python3
import os
import sys
import subprocess
import signal
import socket
import threading

# ————— CONFIGURATION —————
HOST = ''           # listen on all interfaces
PORT = 4000         # must match PI_PORT in your ESP32 sketch

# Paths to your two scripts (don’t change these)
BASE = os.path.dirname(os.path.abspath(__file__))
YOLO_SCRIPT = os.path.join(BASE, "yolo_detect.py")
CTRL_SCRIPT = os.path.join(BASE, "main_combined.py")

# How to launch them (adjust model/source flags if needed)
YOLO_CMD = [
    sys.executable, YOLO_SCRIPT,
    "--model", "best_ncnn_model",
    "--source", "picamera0",
    "--resolution", "1280x720"
]
CTRL_CMD = [sys.executable, CTRL_SCRIPT]

# ————— GLOBALS —————
esp_conn   = None
yolo_proc  = None
ctrl_proc  = None


def start_processes():
    global yolo_proc, ctrl_proc, esp_conn

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

    if ctrl_proc is None or ctrl_proc.poll() is not None:
        ctrl_proc = subprocess.Popen(
            CTRL_CMD,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        threading.Thread(target=monitor_ctrl, daemon=True).start()
        print("✅ CTRL process started")


def stop_processes():
    global yolo_proc, ctrl_proc

    for proc, name in ((yolo_proc, "YOLO"), (ctrl_proc, "CTRL")):
        if proc and proc.poll() is None:
            print(f"🛑 Stopping {name}")
            proc.send_signal(signal.SIGINT)
            proc.wait()

    yolo_proc = None
    ctrl_proc = None


def monitor_ctrl():
    """Read lines from main_combined.py, parse angle, send STEER:… commands."""
    for line in ctrl_proc.stdout:
        print("CTRL |", line, end='')
        if "angle=" in line:
            try:
                angle_str = line.split("angle=")[1].split("°")[0]
                angle = float(angle_str)
                cmd = "STEER:LEFT\n" if angle < 0 else "STEER:RIGHT\n"
                esp_conn.sendall(cmd.encode())
                print(f"→ Sent to ESP32: {cmd.strip()}")
            except Exception:
                pass


def monitor_yolo():
    """Forward any DETECT:… lines from yolo_detect.py to the ESP32."""
    for line in yolo_proc.stdout:
        print("YOLO |", line, end='')
        if line.startswith("DETECT:"):
            esp_conn.sendall((line.strip()+"\n").encode())
            print(f"→ Sent to ESP32: {line.strip()}")


def main():
    global esp_conn

    # 1) Set up TCP server to accept ESP32 connection
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(1)
    print(f"🔌 Waiting for ESP32 on port {PORT}…")
    esp_conn, addr = server.accept()
    print("✅ ESP32 connected from", addr)

    try:
        # 2) Loop, handling incoming gestures
        while True:
            data = esp_conn.recv(1024)
            if not data:
                print("⚠ ESP32 disconnected")
                break

            for line in data.decode().splitlines():
                print("← From ESP32:", line)
                if line.strip() == "GESTURE:INDEX":
                    start_processes()
                elif line.strip() == "GESTURE:CLOSED":
                    stop_processes()

    except KeyboardInterrupt:
        print("\n⚠ Interrupted, shutting down…")

    finally:
        stop_processes()
        if esp_conn:
            esp_conn.close()
        server.close()


if __name__ == "__main__":
    main()
