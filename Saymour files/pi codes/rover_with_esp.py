#!/usr/bin/env python3
import os, sys, signal, socket, subprocess, threading

# ————— CONFIGURATION —————
HOST = ''            # listen on all interfaces
PORT = 5000          # match PI_PORT in FlexHaptic.ino

BASE = os.path.dirname(os.path.abspath(__file__))
CTRL_SCRIPT = os.path.join(BASE, "main_combined.py")
CTRL_CMD = [sys.executable, CTRL_SCRIPT]

esp_conn   = None
ctrl_proc  = None

def start_ctrl():
    global ctrl_proc
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

def stop_ctrl():
    global ctrl_proc
    if ctrl_proc and ctrl_proc.poll() is None:
        print("🛑 Stopping CTRL")
        ctrl_proc.send_signal(signal.SIGINT)
        ctrl_proc.wait()
    ctrl_proc = None

def monitor_ctrl():
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

def main():
    global esp_conn
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(1)
    print(f"🔌 Flex→Steer server listening on port {PORT}…")

    while True:
        esp_conn, addr = server.accept()
        print("✅ ESP32 connected from", addr)
        try:
            while True:
                data = esp_conn.recv(1024)
                if not data:
                    print("⚠ ESP32 disconnected")
                    break
                for line in data.decode().splitlines():
                    print("← From ESP32:", line)
                    if line.strip() == "GESTURE:INDEX":
                        start_ctrl()
                    elif line.strip() == "GESTURE:CLOSED":
                        stop_ctrl()
            stop_ctrl()
            esp_conn.close()
        except KeyboardInterrupt:
            break

    server.close()

if __name__ == "__main__":
    main()