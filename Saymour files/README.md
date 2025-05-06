# Seymour Wearable-Rover System

A GitHub repository for the Seymour assistive rover project, combining an ESP32 glove interface and a Raspberry Pi–driven rover for visually impaired navigation. The system integrates fuzzy‑logic controllers, YOLOv8 object detection, ultrasonic sensors, and haptic/audio feedback.

## Usage

### 1. Full System (Audio + Object Detection + Fuzzy Logic)

* **ESP32**: Upload `esp_wav_player.ino` to ESP.
* **Raspberry Pi**: In `pi/`, activate `venv_fuzzy` and run:

  ```bash
  python run_all_final.py
  ```

### 2. Rover with Vibration Feedback

* **ESP32**: Upload `esp_fuzzy.ino` to ESP.
* **Raspberry Pi**: In `pi/` activate `venv_fuzzy` and run:

  ```bash
  python rover_with_esp.py
  ```

### 3. Model‑Only (Node‑Locked Object Detection)

* **ESP32**: Upload `esp_model.ino`.
* **Raspberry Pi**: In `pi/` activate `venv_fuzzy` and run:

  ```bash
  python model_esp.py
  ```

### 4. Standalone Fuzzy Controllers (Pi Only)

* **Distance Controller**:

  ```bash
  python main1.py
  ```

* **Steering Controller**:

  ```bash
  python main2.py
  ```

* **Combined Controllers**:

  ```bash
  python maincombined.py
  ```

### 5. OpenCV + YOLO Detection

In `pi/`, run:

```bash
python yolo_detect.py --model =best_ncnn_model --source= picamera0 --resolution 1280x720
```

Example:

```bash
python yolo_detect.py --resolution 640x480 --source 0
```

---


