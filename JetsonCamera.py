# Datei: JetsonCamera.py
# MIT License
# Copyright (c) 2019 JetsonHacks

import cv2
import threading
import time

try:
    from Queue import Queue
except ModuleNotFoundError:
    from queue import Queue

def gstreamer_pipeline(
    capture_width=3840,
    capture_height=2160,
    display_width=2560,
    display_height=1440,
    framerate=17,
    flip_method=0, # KEIN Hardware Flip!
):
    return (
        # HIER GEÄNDERT: -0.5 statt -1.2 für helleres Bild
        "nvarguscamerasrc sensor-id=0 exposurecompensation=-0.5 ! "
        "video/x-raw(memory:NVMM), width=(int)%d, height=(int)%d, format=NV12, framerate=(fraction)%d/1 ! "
        "nvvidconv flip-method=%d ! "
        "video/x-raw, width=(int)%d, height=(int)%d, format=BGRx ! "
        "videoconvert ! "
        "video/x-raw, format=BGR ! appsink sync=false drop=true"
        % (
            capture_width,
            capture_height,
            framerate,
            flip_method,
            display_width,
            display_height,
        )
    )

class FrameReader(threading.Thread):
    queues = []
    _running = True
    camera = None
    def __init__(self, camera, name):
        threading.Thread.__init__(self)
        self.name = name
        self.camera = camera
 
    def run(self):
        while self._running:
            _, frame = self.camera.read()
            while self.queues:
                queue = self.queues.pop()
                queue.put(frame)
    
    def addQueue(self, queue):
        self.queues.append(queue)

    def getFrame(self, timeout = None):
        queue = Queue(1)
        self.addQueue(queue)
        return queue.get(timeout = timeout)

    def stop(self):
        self._running = False

class Previewer(threading.Thread):
    window_name = "Arducam"
    _running = True
    camera = None
    def __init__(self, camera, name):
        threading.Thread.__init__(self)
        self.name = name
        self.camera = camera
    
    def run(self):
        self._running = True
        while self._running:
            cv2.imshow(self.window_name, self.camera.getFrame(2000))
            keyCode = cv2.waitKey(16) & 0xFF
        cv2.destroyWindow(self.window_name)

    def start_preview(self):
        self.start()
    def stop_preview(self):
        self._running = False

class Camera(object):
    frame_reader = None
    cap = None
    previewer = None

    def __init__(self, width=2560, height=1440):
        self.open_camera(width, height)

    def open_camera(self, width=2560, height=1440):
        pipeline = gstreamer_pipeline(
            capture_width=3840, 
            capture_height=2160,
            display_width=width, 
            display_height=height,
            framerate=17, 
            flip_method=0 
        )
        print(f"GStreamer Pipeline: {pipeline}")

        self.cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
        
        if not self.cap.isOpened():
            raise RuntimeError("Failed to open camera!")
            
        if self.frame_reader == None:
            self.frame_reader = FrameReader(self.cap, "")
            self.frame_reader.daemon = True
            self.frame_reader.start()
        self.previewer = Previewer(self.frame_reader, "")

    def getFrame(self, timeout = None):
        return self.frame_reader.getFrame(timeout)

    def start_preview(self):
        self.previewer.daemon = True
        self.previewer.start_preview()

    def stop_preview(self):
        self.previewer.stop_preview()
        self.previewer.join()
    
    def close(self):
        self.frame_reader.stop()
        self.cap.release()
