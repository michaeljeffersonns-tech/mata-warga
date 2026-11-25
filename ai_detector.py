import os
from ultralytics import YOLO

# Mengambil direktori tempat file ai_detector.py berada (yaitu folder 'backend')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Menggabungkan path secara otomatis, jadi mau dijalankan dari mana pun tetap aman
MODEL_PATH = os.path.join(BASE_DIR, "weights", "best.pt") 


class YoloDetector:
    def __init__(self):
        print(f"[AI] Memuat model kustom YOLO dari {MODEL_PATH}...")
        self.model = YOLO(MODEL_PATH)
        print("[AI] Model kustom berhasil dimuat!")

    def detect(self, image_path: str, violation_type: str):
        results = self.model(image_path, verbose=False)[0]
        
        detected_no_helmet = False
        max_conf = 0.0
        detected_objects = []

        for box in results.boxes:
            cls_id = int(box.cls[0])
            label = self.model.names[cls_id]
            conf = float(box.conf[0])
            detected_objects.append(f"{label} ({conf:.2f})")
            
            if "without" in label.lower():
                detected_no_helmet = True
                if conf > max_conf:
                    max_conf = conf

        if violation_type == "helmet":
            if detected_no_helmet and max_conf > 0.40:
                accepted = True
                confidence = round(max_conf, 3)
                reason = f"AI mendeteksi pengendara TANPA HELM (Keyakinan: {confidence*100:.1f}%)."
            else:
                accepted = False
                confidence = 0.20
                reason = "AI tidak menemukan pelanggaran helm yang jelas pada gambar ini."
                
        elif violation_type in ["wrong_way", "red_light"]:
            if len(results.boxes) > 0:
                accepted = True
                confidence = 0.65
                reason = f"Kendaraan terdeteksi. Validator harap cek manual arah/lampu. Objek: {', '.join(detected_objects)}"
            else:
                accepted = False
                confidence = 0.30
                reason = "Tidak ada kendaraan yang terdeteksi di gambar."
        else:
            accepted = False
            confidence = 0.10
            reason = "Jenis pelanggaran tidak dikenali."

        return {
            "accepted": accepted,
            "confidence": confidence,
            "reason": reason,
            "plate_guess": None,
            "engine": "yolo-custom"
        }

def get_detector():
    try:
        return YoloDetector()
    except Exception as e:
        print(f"[ERROR] Gagal memuat model: {e}")
        return YoloDetector() # Biarkan error agar kelihatan jika best.pt belum ada

DETECTOR = get_detector()