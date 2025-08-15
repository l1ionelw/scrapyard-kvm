import cv2
import os
import platform
from datetime import datetime

def get_camera_names():
    """
    Get camera names using system-specific methods
    Returns a dictionary mapping camera index to name
    """
    camera_names = {}
    system = platform.system()
    
    if system == "Windows":
        try:
            import subprocess
            # Use PowerShell to get camera names
            result = subprocess.run([
                "powershell", "-Command",
                "Get-WmiObject -Class Win32_PnPEntity | Where-Object {$_.PNPClass -eq 'Camera' -or $_.Name -like '*camera*' -or $_.Name -like '*capture*'} | Select-Object Name, DeviceID"
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                idx = 0
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('Name') and not line.startswith('----'):
                        if line:
                            camera_names[idx] = line.split()[0] if line.split() else f"Camera {idx}"
                            idx += 1
        except:
            pass
    
    elif system == "Linux":
        try:
            # Try to read from /sys/class/video4linux/
            import glob
            for device_path in glob.glob('/sys/class/video4linux/video*/name'):
                try:
                    device_num = int(device_path.split('video')[1].split('/')[0])
                    with open(device_path, 'r') as f:
                        name = f.read().strip()
                        camera_names[device_num] = name
                except:
                    continue
        except:
            pass
    
    elif system == "Darwin":  # macOS
        try:
            import subprocess
            # Use system_profiler to get camera info
            result = subprocess.run([
                "system_profiler", "SPCameraDataType"
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                # Parse the output to extract camera names
                # This is a simplified parser
                lines = result.stdout.split('\n')
                idx = 0
                for line in lines:
                    if ':' in line and 'Camera' in line:
                        name = line.split(':')[0].strip()
                        camera_names[idx] = name
                        idx += 1
        except:
            pass
    
    return camera_names

def list_cameras(max_cameras=10):
    """
    List all available cameras/capture devices
    Returns a list of tuples (index, name/info)
    """
    available_cameras = []
    
    print("Scanning for available cameras...")
    
    # Get system-specific camera names
    camera_names = get_camera_names()
    
    for i in range(max_cameras):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            # Try to get some info about the camera
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            # Get camera name from system info or fallback
            if i in camera_names:
                camera_name = camera_names[i]
            else:
                try:
                    backend_name = cap.getBackendName()
                    camera_name = f"Device {i} ({backend_name})"
                except:
                    camera_name = f"Camera {i}"
            
            # Try to read a frame to confirm it's working
            ret, frame = cap.read()
            if ret:
                available_cameras.append((i, f"{camera_name} - Resolution: {width}x{height}, FPS: {fps:.1f}"))
            
            cap.release()
    
    return available_cameras

def capture_frame(camera_index, output_filename=None):
    """
    Capture a single frame from the specified camera
    """
    if output_filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"captured_frame_{timestamp}.jpg"
    
    # Initialize camera
    cap = cv2.VideoCapture(camera_index)
    
    if not cap.isOpened():
        print(f"Error: Could not open camera {camera_index}")
        return False
    
    # Set camera properties (optional - adjust as needed)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
    
    print(f"Initializing camera {camera_index}...")
    
    # Let camera warm up and stabilize
    for i in range(10):
        ret, frame = cap.read()
        if not ret:
            print(f"Error: Could not read frame from camera {camera_index}")
            cap.release()
            return False
    
    # Capture the final frame
    ret, frame = cap.read()
    
    if ret:
        # Save the frame
        success = cv2.imwrite(output_filename, frame)
        if success:
            print(f"Frame captured and saved as: {output_filename}")
            print(f"Image size: {frame.shape[1]}x{frame.shape[0]} pixels")
        else:
            print(f"Error: Could not save image to {output_filename}")
            cap.release()
            return False
    else:
        print("Error: Could not capture frame")
        cap.release()
        return False
    
    cap.release()
    return True

def main():
    print("=== Camera Capture Tool ===\n")
    
    # List available cameras
    cameras = list_cameras()
    
    if not cameras:
        print("No cameras found!")
        return
    
    print("\nAvailable cameras:")
    for idx, info in cameras:
        print(f"  {idx}: {info}")
    
    # Let user select camera
    while True:
        try:
            choice = input(f"\nSelect camera index (0-{len(cameras)-1}): ")
            camera_index = int(choice)
            
            # Verify the choice is valid
            valid_indices = [cam[0] for cam in cameras]
            if camera_index in valid_indices:
                break
            else:
                print(f"Invalid choice. Please select from: {valid_indices}")
        
        except ValueError:
            print("Please enter a valid number.")
        except KeyboardInterrupt:
            print("\nOperation cancelled.")
            return
    
    # Get output filename (optional)
    output_file = input("\nEnter output filename (press Enter for auto-generated): ").strip()
    if not output_file:
        output_file = None
    
    # Capture frame
    print(f"\nCapturing from camera {camera_index}...")
    success = capture_frame(camera_index, output_file)
    
    if success:
        print("Capture completed successfully!")
    else:
        print("Capture failed!")

if __name__ == "__main__":
    main()