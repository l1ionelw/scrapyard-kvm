import cv2
import threading
import time
from flask import Flask, Response, render_template, request, jsonify, redirect
import json
import logging
from queue import Queue
import numpy as np
# Env variable OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS = 0 on some devices for faster camera startup

# --- Configuration ---
CAMERA_INDEX = 0  # Change this to your capture card's index (e.g., 0, 1, 2)
CAMERA_NAME = "Capture Card Stream"  # A descriptive name for your stream
JPEG_QUALITY = 85  # Image quality (0-100), higher is better quality but more data
IDLE_TIMEOUT = 5  # Seconds to wait before stopping the camera when no one is watching
BUFFER_SIZE = 2  # Keep only the latest N frames to reduce latency
TARGET_FPS = 24  # Target frame rate

# --- Flask App Initialization ---
app = Flask(__name__, template_folder='.')

# --- Global Variables ---
camera = None
camera_lock = threading.Lock()
frame_queue = Queue(maxsize=BUFFER_SIZE)
latest_frame = None
last_access_time = None
capture_thread = None
active_viewers = 0
viewer_lock = threading.Lock()
REINIT_CAMERA = False



def camera_manager():
    """
    A thread that manages the camera resource.
    It starts the camera when the first viewer connects and stops it when the last one leaves.
    """
    global camera, latest_frame, last_access_time, capture_thread, REINIT_CAMERA

    while True:
        if REINIT_CAMERA:
            with camera_lock:
                if camera:
                    print("Re-initializing camera with new settings.")
                    camera.release()
                    camera = None
                    REINIT_CAMERA = False

        with viewer_lock:
            current_viewers = active_viewers

        if current_viewers == 0 and last_access_time and (time.time() - last_access_time) > IDLE_TIMEOUT:
            with camera_lock:
                if camera:
                    print("Stopping camera due to inactivity.")
                    camera.release()
                    camera = None
                    # Clear the frame queue
                    while not frame_queue.empty():
                        try:
                            frame_queue.get_nowait()
                        except:
                            break
            last_access_time = None

        time.sleep(1)

def capture_frames():
    """
    Optimized frame capture loop that runs in a background thread.
    """
    global latest_frame, camera
    
    frame_interval = 1.0 / TARGET_FPS
    last_frame_time = 0
    
    while True:
        with camera_lock:
            if not camera:
                time.sleep(0.1)
                continue

        current_time = time.time()
        
        # Control frame rate
        if current_time - last_frame_time < frame_interval:
            time.sleep(0.001)  # Very short sleep to prevent CPU spinning
            continue
            
        ret, frame = camera.read()
        
        if ret:
            config = get_config()
            if config['flip_camera']:
                frame = cv2.flip(frame, 1)
            # Encode frame to JPEG
            encode_params = [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY]
            _, buffer = cv2.imencode('.jpg', frame, encode_params)
            frame_bytes = buffer.tobytes()
            
            # Update latest frame (thread-safe)
            latest_frame = frame_bytes
            
            # Add to queue, removing old frames if queue is full
            if frame_queue.full():
                try:
                    frame_queue.get_nowait()  # Remove oldest frame
                except:
                    pass
            
            try:
                frame_queue.put_nowait(frame_bytes)
            except:
                pass  # Queue might be full, skip this frame
                
            last_frame_time = current_time
        else:
            print("Failed to read frame from camera.")
            time.sleep(0.1)

def initialize_camera():
    """Initializes the camera with optimized settings."""
    global camera, capture_thread
    config = get_config()
    width, height = map(int, config['resolution'].split('x'))
    
    with camera_lock:
        if camera is None:
            print(f"Initializing camera (index: {CAMERA_INDEX})...")
            camera = cv2.VideoCapture(CAMERA_INDEX)
            
            if not camera.isOpened():
                print(f"Error: Could not open camera {CAMERA_INDEX}.")
                camera = None
                return False
            
            # Optimize camera settings for low latency
            print("Setting camera properties")
            print(f"Camera resolution: {width}x{height}")
            camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce internal buffer
            camera.set(cv2.CAP_PROP_FPS, TARGET_FPS)
            camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            
            print("Camera initialized successfully.")

            # Start the capture thread
            if capture_thread is None or not capture_thread.is_alive():
                capture_thread = threading.Thread(target=capture_frames, daemon=True)
                capture_thread.start()
                
    return True

def generate_frames():
    """
    Optimized generator function that yields the latest frames.
    """
    global last_access_time, active_viewers

    # Increment viewer count
    with viewer_lock:
        active_viewers += 1
    
    if not initialize_camera():
        # Decrement viewer count if initialization fails
        with viewer_lock:
            active_viewers -= 1
        return

    print(f"Viewer connected. Total viewers: {active_viewers}")
    
    try:
        while True:
            last_access_time = time.time()
            
            # Get the latest frame
            if latest_frame:
                yield (
                    b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' +
                    latest_frame +
                    b'\r\n'
                )
            
            # Small sleep to prevent overwhelming the client
            time.sleep(1.0 / TARGET_FPS)
            
    except GeneratorExit:
        # Client disconnected
        pass
    finally:
        # Decrement viewer count
        with viewer_lock:
            active_viewers -= 1
        print(f"Viewer disconnected. Total viewers: {active_viewers}")

@app.route('/')
def index():
    return "nihao"

@app.route('/mario')
def show_video():
    """Render the main streaming page."""
    global camera
    config = get_config()
    width = "0"
    height = "0"
    fps = "0"
    if camera: 
        width  = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = camera.get(cv2.CAP_PROP_FPS)
    return render_template("templates/index.html", camera_name=CAMERA_NAME, show_text=config['show_text'], broadcast_resolution=f"{width}x{height}@{fps}")

@app.route('/mario-better')
def show_video_better():
    """Render the main streaming page."""
    global camera
    config = get_config()
    width = "0"
    height = "0"
    fps = "0"
    if camera: 
        width  = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = camera.get(cv2.CAP_PROP_FPS)
    return render_template("templates/index-with-passthrough.html", camera_name=CAMERA_NAME, show_text=config['show_text'], broadcast_resolution=f"{width}x{height}@{fps}")


@app.route('/luigi')
def test_keyboard():
    return render_template("templates/test_simple_keyboard_typing.html")

@app.route('/luigi-better')
def test_keyboard_better():
    return render_template("templates/test_keyboard_passthrough.html")
@app.route('/control-plane')
def test_control_plane():
    return render_template("templates/test_control_plane.html")

def get_config():
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
            if 'unlocked_scaling' not in config:
                config['unlocked_scaling'] = False
            return config
    except FileNotFoundError:
        # Create a default config if the file doesn't exist
        default_config = {
            'resolution': '1280x720',
            'flip_camera': False,
            'show_text': True,
            'unlocked_scaling': False
        }
        save_config(default_config)
        return default_config

def save_config(config):
    with open('config.json', 'w') as f:
        json.dump(config, f, indent=4)

@app.route('/settings')
def settings():
    config = get_config()
    return render_template('templates/settings_capture_card.html', config=config,current_resolution=config["resolution"])

REINIT_CAMERA = False

@app.route('/save_settings', methods=['POST'])
def save_settings():
    global REINIT_CAMERA
    config = get_config()
    config['resolution'] = request.form.get('resolution', config['resolution'])
    config['flip_camera'] = request.form.get('flip_camera') == 'true'
    config['show_text'] = request.form.get('show_text') == 'true'
    config['unlocked_scaling'] = request.form.get('unlocked_scaling') == 'true'
    save_config(config)
    REINIT_CAMERA = True
    return redirect('/settings')

@app.route('/video_feed')
def video_feed():
    """The video streaming route."""
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    # Disable werkzeug's default logging to keep the console clean
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

    # Start the camera manager thread
    manager_thread = threading.Thread(target=camera_manager, daemon=True)
    manager_thread.start()

    print("=====================================")
    print(f"  {CAMERA_NAME} - Web Streamer")
    print("=====================================")
    print(f"URL: http://localhost:5001")
    print("Press Ctrl+C to stop the server.")
    app.run(host='0.0.0.0', port=5001, threaded=True)