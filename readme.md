# Scrapyard KVM

Scrapyard KVM is a DIY remote KVM (Keyboard, Video, Mouse) solution that allows people to access and control a PC’s GPU output remotely using an embedded device such as a Raspberry Pi. This project leverages a capture card to stream video from a server PC and a microcontroller (like an Arduino) to send mouse inputs. It provides flexible, and customizable remote access for enthusiasts who want to manage their hardware without buying commercial KVM solutions.

---

## What is KVM?

KVM stands for **Keyboard, Video, Mouse**. A KVM system allows a you to control a computer from a remote location by sending keyboard and mouse input while receiving video output from the computer. It's better than remote desktop because it bypasses the OS, allowing you to see the BIOS and all hardware output just as if it were a real monitor. This is commonly used in server management, remote IT setups, or multi-PC environments. Scrapyard KVM provides this functionality in a DIY format, giving you flexibility over hardware, scaling, and other technical parameters.

---

## FYI
This project was made by me (l1ionelw) to troubleshoot and easy access to my server PC. The materials required may cost more than a traditional kvm (jetkvm). However it IS open source (so is jetkvm). But its more easy to modify if you want a custom setup or smh, idc.

## Project Overview

Scrapyard KVM works by connecting your server PC to a capture card via HDMI. The capture card then sends the video output to an embedded device (like a Raspberry Pi) which hosts a web server. Remote users can access this server to view and interact with the GPU output of the server PC. Mouse input is sent back to the server via an Arduino (or any microcontroller capable of sending HID packets).

**Hardware Requirements:**

- Server PC with GPU output (HDMI)
- HDMI Capture Card (tested with EVGA XR1 Lite)
- Embedded device with USB support (e.g., Raspberry Pi)
- Arduino or microcontroller capable of sending mouse HID packets
- HDMI cables

**Software Components:**

1. **Server files**: Run on the Raspberry Pi or embedded device to host the web interface.
2. **Arduino INO file**: Handles mouse input communication to the server PC.

---

## Features

- Remote KVM access over the web
- Unrestricted video scaling (does not enforce aspect ratio)
- Configurable capture card aspect ratio
- Optional display of technical/debugging stats
- Simple DIY setup using affordable hardware
- Lightweight and easily portable

---

## Installation

### 1. Server Setup (Raspberry Pi / Embedded Device)

1. Clone this repository to your Raspberry Pi:
   ```bash
   git clone https://github.com/yourusername/scrapyard-kvm.git
   cd scrapyard-kvm
2. Install necessary dependencies
    ```bash
    sudo apt update
    pip install -r requirements.txt
    ```
3. Run the server
    ```bash
    cd server && python server.py
    ```
4. Navigate to the raspberry pi IP address at port 5000 in your browser (find IP using ```ip a```)
    ```bash
    https://<raspberrypi-ip>:5000
    https://192.168.1.20:5000
    ```
### 2. Arduino Setup

1. Open the scrapyard\_kvm.ino file in the Arduino IDE.

2. Upload it to your Arduino or HID-capable microcontroller.

3. Connect the microcontroller to the Raspberry Pi via USB.

### 3. Hardware Connections

1. Connect capture card to PC.

2. Connect the capture card output usb or usb-c to the Raspberry Pi (USB). 

3. Also connect raspberry pi to arduino via USB (uses usb host shield).

### Features
Web interface allows you to see capture card output just like if you had a monitor plugged in. Since this replicates HDMI at a hardware level, it allows you to see boot screens and change BIOS settings.
- Resolution Changing (currently hardcoded resolutions are for EVGA XR1 Lite capture card)
- Flip camera (for actual camera) so it looks like looking into a mirror
- Show debug details such as resolution, fps, etc
- Unlocked scaling so that display fills the screen no matter of aspect ratio
- ZERO encryption/ login (this is a feature. PULEASE do not port forward. Use vpn from outside network)



### Acknowledgements
Big thanks to chatgpt, gemini, and claude. Decreased coding time from a week to an hour :)

Thank you OpenCV. Donate here: https://opencv.org/support/