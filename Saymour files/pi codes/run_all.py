#!/usr/bin/env python3
import subprocess, signal, sys, os

def main():
    # Make sure we use the same python as this launcher
    PY = sys.executable

    # Paths to your two scripts
    BASE = os.path.dirname(os.path.abspath(__file__))
    YOLO = os.path.join(BASE, "yolo_detect.py")
    CTRL = os.path.join(BASE, "main_combined.py")

    procs = []
    try:
        # 1) Start YOLO detection
        #    Adjust --model and --source to your needs:
        procs.append(subprocess.Popen([
            PY, YOLO,
            "--model", "best_ncnn_model",
            "--source", "picamera0",
            "--resolution", "1280x720"
        ]))

        # 2) Start your fuzzy + rover control loop
        procs.append(subprocess.Popen([PY, CTRL]))

        # 3) Wait for either process to exit (or for Ctrl+C)
        for p in procs:
            p.wait()

    except KeyboardInterrupt:
        print("\nShutting down…")
        # send SIGINT to both so they can clean up GPIO, windows, etc.
        for p in procs:
            p.send_signal(signal.SIGINT)
        for p in procs:
            p.wait()

if __name__ == "__main__":
    main()
