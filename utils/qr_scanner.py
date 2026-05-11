from pyzbar.pyzbar import decode
import cv2


def scan_image_file(path):
    image = cv2.imread(path)
    if image is None:
        return None
    decoded = decode(image)
    if not decoded:
        return None
    return decoded[0].data.decode("utf-8")


def webcam_scan_once(camera_index=0):
    camera = cv2.VideoCapture(camera_index)
    try:
        ok, frame = camera.read()
        if not ok:
            return None
        decoded = decode(frame)
        return decoded[0].data.decode("utf-8") if decoded else None
    finally:
        camera.release()
