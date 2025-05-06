import sys
print(f"=== DEBUG: yolo_detect running under {sys.executable} ({sys.version.splitlines()[0]}) ===")
try:
    import cv2
    print(f"=== DEBUG: Imported cv2 v{cv2.__version__} from {cv2.__file__} ===", flush=True)
except Exception as e:
    print("=== DEBUG: Failed to import cv2:", e, flush=True)
    sys.exit(1)

import os
import argparse
import glob
import time
import numpy as np
from ultralytics import YOLO

# Define and parse user input arguments
parser = argparse.ArgumentParser()
parser.add_argument('--model', help='Path to YOLO model file (example: "runs/detect/train/weights/best.pt")',
                    required=True)
parser.add_argument('--source', help='Image source, can be image file ("test.jpg"), \
                    image folder ("test_dir"), video file ("testvid.mp4"), or index of USB camera ("usb0")',
                    required=True)
parser.add_argument('--thresh', help='Minimum confidence threshold for displaying detected objects (example: "0.4")',
                    default=0.5)
parser.add_argument('--resolution', help='Resolution in WxH to display inference results at (example: "640x480"), \
                    otherwise, match source resolution',
                    default=None)
parser.add_argument('--record', help='Record results from video or webcam and save it as "demo1.avi". Must specify --resolution argument to record.',
                    action='store_true')
args = parser.parse_args()

# Parse user inputs
model_path = args.model
img_source = args.source
min_thresh = float(args.thresh)
user_res = args.resolution
record = args.record

# Check if model file exists and is valid
if not os.path.exists(model_path):
    print('ERROR: Model path is invalid or model was not found. Make sure the model filename was entered correctly.')
    sys.exit(0)

# Load the model into memory and get labemap
model = YOLO(model_path, task='detect')
labels = model.names

# Determine source type
img_ext_list = ['.jpg','.JPG','.jpeg','.JPEG','.png','.PNG','.bmp','.BMP']
vid_ext_list = ['.avi','.mov','.mp4','.mkv','.wmv']

if os.path.isdir(img_source):
    source_type = 'folder'
elif os.path.isfile(img_source):
    _, ext = os.path.splitext(img_source)
    if ext in img_ext_list:
        source_type = 'image'
    elif ext in vid_ext_list:
        source_type = 'video'
    else:
        print(f'File extension {ext} is not supported.')
        sys.exit(0)
elif 'usb' in img_source:
    source_type = 'usb'
    usb_idx = int(img_source[3:])
elif 'picamera' in img_source:
    source_type = 'picamera'
    picam_idx = int(img_source[8:])
else:
    print(f'Input {img_source} is invalid. Please try again.')
    sys.exit(0)

# Parse display resolution
resize = False
if user_res:
    resize = True
    resW, resH = map(int, user_res.split('x'))

# Recording setup
if record:
    if source_type not in ['video','usb']:
        print('Recording only works for video and camera sources. Please try again.')
        sys.exit(0)
    if not user_res:
        print('Please specify resolution to record video at.')
        sys.exit(0)
    record_name = 'demo1.avi'
    record_fps = 30
    recorder = cv2.VideoWriter(record_name, cv2.VideoWriter_fourcc(*'MJPG'), record_fps, (resW,resH))

# Initialize image source
if source_type == 'image':
    imgs_list = [img_source]
elif source_type == 'folder':
    imgs_list = [f for f in glob.glob(img_source + '/*') if os.path.splitext(f)[1] in img_ext_list]
elif source_type in ['video', 'usb']:
    cap_arg = usb_idx if source_type == 'usb' else img_source
    cap = cv2.VideoCapture(cap_arg)
    if user_res:
        cap.set(3, resW)
        cap.set(4, resH)
elif source_type == 'picamera':
    from picamera2 import Picamera2
    cap = Picamera2()
    cap.configure(cap.create_video_configuration(main={"format": 'XRGB8888', "size": (resW, resH)}))
    cap.start()

# Colors for bounding boxes
bbox_colors = [(164,120,87), (68,148,228), (93,97,209), (178,182,133), (88,159,106),
               (96,202,231), (159,124,168), (169,162,241), (98,118,150), (172,176,184)]

# Loop variables
avg_frame_rate = 0
frame_rate_buffer = []
fps_avg_len = 200
img_count = 0

# Inference loop
while True:
    t_start = time.perf_counter()

    # Read frame
    if source_type in ['image', 'folder']:
        if img_count >= len(imgs_list):
            print('All images have been processed. Exiting program.')
            sys.exit(0)
        frame = cv2.imread(imgs_list[img_count])
        img_count += 1
    elif source_type in ['video', 'usb']:
        ret, frame = cap.read()
        if not ret or frame is None:
            print('Stream ended or camera error. Exiting program.')
            break
    else:  # picamera
        frame_bgra = cap.capture_array()
        frame = cv2.cvtColor(frame_bgra, cv2.COLOR_BGRA2BGR)

    # Resize if needed
    if resize:
        frame = cv2.resize(frame, (resW, resH))

    # Run inference
    results = model(frame, verbose=False)
    detections = results[0].boxes
    object_count = 0

    # Process detections
    for det in detections:
        xyxy = det.xyxy.cpu().numpy().squeeze().astype(int)
        xmin, ymin, xmax, ymax = xyxy
        classidx = int(det.cls.item())
        classname = labels[classidx]
        conf = det.conf.item()

        if conf > min_thresh:
            color = bbox_colors[classidx % len(bbox_colors)]
            cv2.rectangle(frame, (xmin, ymin), (xmax, ymax), color, 2)
            label = f"{classname}: {int(conf*100)}%"
            labelSize, baseLine = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            label_ymin = max(ymin, labelSize[1] + 10)
            cv2.rectangle(frame, (xmin, label_ymin - labelSize[1] - 10),
                          (xmin + labelSize[0], label_ymin + baseLine - 10), color, cv2.FILLED)
            cv2.putText(frame, label, (xmin, label_ymin - 7), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,0), 1)

            # Debug: notify run_all.py
            print(f"DETECT:{classname}", flush=True)

            object_count += 1

    # Display framerate and count
    if source_type in ['video', 'usb', 'picamera']:
        cv2.putText(frame, f'FPS: {avg_frame_rate:.2f}', (10,20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,255), 2)
    cv2.putText(frame, f'Number of objects: {object_count}', (10,40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,255), 2)

    # Show frame
    cv2.imshow('YOLO detection results', frame)
    if record:
        recorder.write(frame)

    key = cv2.waitKey(5)
    if key in [ord('q'), ord('Q')]:
        break
    elif key in [ord('s'), ord('S')]:
        cv2.waitKey()
    elif key in [ord('p'), ord('P')]:
        cv2.imwrite('capture.png', frame)

    # Update framerate
    t_stop = time.perf_counter()
    frame_rate_buffer.append(1.0 / (t_stop - t_start))
    if len(frame_rate_buffer) > fps_avg_len:
        frame_rate_buffer.pop(0)
    avg_frame_rate = float(np.mean(frame_rate_buffer))

# Cleanup
print(f'Average pipeline FPS: {avg_frame_rate:.2f}')
if source_type in ['video', 'usb']:
    cap.release()
elif source_type == 'picamera':
    cap.stop()
if record:
    recorder.release()
cv2.destroyAllWindows()
