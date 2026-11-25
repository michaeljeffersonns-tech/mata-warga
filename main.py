import os
import uuid
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from database import init_db, add_report, get_reports, get_report, update_status, get_stats
from ai_detector import DETECTOR

# Setup Folder Upload
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI(title="Mata Warga API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    init_db()

# ---------- ENDPOINT API ----------

@app.post("/api/reports")
async def submit_report(
    violation_type: str = Form(...),
    plate_number: str = Form(""),
    lat: float = Form(0.0),
    lng: float = Form(0.0),
    photo: UploadFile = File(...),
):
    if violation_type not in ("helmet", "wrong_way", "red_light"):
        raise HTTPException(400, "Jenis pelanggaran tidak didukung")

    ext = photo.filename.split(".")[-1].lower() if "." in photo.filename else "jpg"
    fname = f"{uuid.uuid4().hex}.{ext}"
    fpath = os.path.join(UPLOAD_DIR, fname)
    with open(fpath, "wb") as f:
        f.write(await photo.read())

    ai = DETECTOR.detect(fpath, violation_type)

    rid = add_report(
        violation_type=violation_type,
        plate_number=plate_number.strip().upper(),
        lat=lat, lng=lng,
        photo_path=fname,
        ai_confidence=ai["confidence"],
        ai_reason=ai["reason"],
    )

    return {
        "id": rid,
        "ai": ai,
        "status": "pending" if ai["accepted"] else "ai_rejected",
        "message": ("Laporan diterima, menunggu validasi Polri."
                    if ai["accepted"] else "AI menilai bukti kurang jelas."),
    }

@app.get("/api/reports")
def list_reports(status: str = None):
    return get_reports(status)

@app.get("/api/stats")
def stats():
    return get_stats()

@app.post("/api/police/validate/{rid}")
def police_validate(rid: int, status: str = Form(...), note: str = Form("")):
    if status not in ("valid", "rejected"):
        raise HTTPException(400, "Status tidak valid")

    r = get_report(rid)
    if not r:
        raise HTTPException(404, "Laporan tidak ditemukan")

    DENDA = {"helmet": 250000, "wrong_way": 500000, "red_light": 500000}
    reward = int(DENDA.get(r["violation_type"], 250000) * 0.10) if status == "valid" else 0

    update_status(rid, status, reward, note)
    return {"id": rid, "status": status, "reward": reward}


# ==========================================
# PENGATURAN FILE STATIS & FRONTEND
# ==========================================

# 1. Serve folder uploads agar gambar bisa dilihat
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# 2. Serve file statis frontend (CSS, JS, Gambar) dari folder backend
app.mount("/static", StaticFiles(directory=BASE_DIR), name="static")

# 3. Serve halaman utama HTML
@app.get("/")
def serve_index():
    return FileResponse(os.path.join(BASE_DIR, "index.html"))