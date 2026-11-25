const API = "";  // same-origin; ganti jika backend beda host

// ===== Navigasi Tab =====
document.querySelectorAll("nav button").forEach(btn => {
  btn.onclick = () => {
    document.querySelectorAll("nav button").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".panel").forEach(p => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById("tab-" + btn.dataset.tab).classList.add("active");
    if (btn.dataset.tab === "police") loadPolice();
    if (btn.dataset.tab === "feed") loadFeed();
  };
});

// ===== Toast =====
function toast(msg, color = "#0ea5e9") {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.style.background = color;
  t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), 3000);
}

// ===== Stats =====
async function loadStats() {
  const r = await fetch(API + "/api/stats");
  const s = await r.json();
  document.getElementById("stats-box").innerHTML = `
    <div class="stat"><div class="num">${s.total}</div><div class="lbl">Total Laporan</div></div>
    <div class="stat"><div class="num">${s.pending}</div><div class="lbl">Menunggu</div></div>
    <div class="stat"><div class="num">${s.valid}</div><div class="lbl">Valid</div></div>
    <div class="stat"><div class="num">Rp ${s.total_reward.toLocaleString('id-ID')}</div><div class="lbl">Kompensasi</div></div>
  `;
}

// ===== Kamera Live =====
let stream = null;
const video = document.getElementById("camera");
const canvas = document.getElementById("snapshot");

document.getElementById("btn-camera").onclick = async () => {
  try {
    stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
    video.srcObject = stream;
    video.style.display = "block";
    document.getElementById("btn-camera").style.display = "none";
    document.getElementById("btn-capture").style.display = "block";
  } catch (e) {
    toast("Kamera tidak tersedia: " + e.message, "#ef4444");
  }
};

document.getElementById("btn-capture").onclick = () => {
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  canvas.getContext("2d").drawImage(video, 0, 0);
  canvas.toBlob(blob => {
    const file = new File([blob], "capture.jpg", { type: "image/jpeg" });
    const dt = new DataTransfer();
    dt.items.add(file);
    document.getElementById("photo").files = dt.files;
    toast("Foto berhasil diambil ✅");
  }, "image/jpeg", 0.92);
};

// ===== Submit Laporan =====
document.getElementById("btn-submit").onclick = async () => {
  const file = document.getElementById("photo").files[0];
  if (!file) return toast("Silakan ambil/pilih foto bukti dulu.", "#ef4444");

  const fd = new FormData();
  fd.append("violation_type", document.getElementById("violation_type").value);
  fd.append("plate_number", document.getElementById("plate_number").value);
  fd.append("photo", file);

  // Lokasi GPS
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
      pos => {
        fd.append("lat", pos.coords.latitude);
        fd.append("lng", pos.coords.longitude);
        sendReport(fd);
      },
      () => { fd.append("lat", 0); fd.append("lng", 0); sendReport(fd); },
      { timeout: 5000 }
    );
  } else {
    fd.append("lat", 0); fd.append("lng", 0); sendReport(fd);
  }
};

async function sendReport(fd) {
  document.getElementById("btn-submit").disabled = true;
  try {
    const r = await fetch(API + "/api/reports", { method: "POST", body: fd });
    if (!r.ok) throw new Error(await r.text());
    const data = await r.json();

    const ai = data.ai;
    const box = document.getElementById("ai-box");
    box.classList.add("show");
    box.innerHTML = `
      <strong>🤖 Hasil Pra-Pemeriksaan AI (${ai.engine})</strong><br>
      Keyakinan: <span class="conf">${(ai.confidence * 100).toFixed(1)}%</span><br>
      ${ai.reason}<br><br>
      <em>${data.message}</em>
    `;
    toast("Laporan terkirim! ID #" + data.id, "#22c55e");
    loadStats();
  } catch (e) {
    toast("Gagal kirim: " + e.message, "#ef4444");
  } finally {
    document.getElementById("btn-submit").disabled = false;
  }
}

// ===== Panel Polisi =====
async function loadPolice() {
  const r = await fetch(API + "/api/reports?status=pending");
  const list = await r.json();
  const el = document.getElementById("police-list");
  if (!list.length) { el.innerHTML = '<div class="card"><p class="hint">Tidak ada laporan menunggu.</p></div>'; return; }

  el.innerHTML = list.map(rep => `
    <div class="report pending">
      <div class="row">
        <img class="thumb" src="/uploads/${rep.photo_path}" alt="bukti">
        <div class="meta">
          <strong>#${rep.id} — ${labelOf(rep.violation_type)}</strong><br>
          Plat: ${rep.plate_number || "-"} · AI: ${(rep.ai_confidence * 100).toFixed(0)}%<br>
          ${rep.ai_reason}<br>
          <span class="status-tag">${rep.status}</span>
          <div style="margin-top:10px; display:flex; gap:8px;">
            <button class="btn green" style="width:auto; margin:0; padding:8px 16px;"
              onclick="validate(${rep.id}, 'valid')">✔ Valid</button>
            <button class="btn red" style="width:auto; margin:0; padding:8px 16px;"
              onclick="validate(${rep.id}, 'rejected')">✖ Tolak</button>
          </div>
        </div>
      </div>
    </div>
  `).join("");
}

async function validate(id, status) {
  const fd = new FormData();
  fd.append("status", status);
  fd.append("note", status === "valid" ? "Terverifikasi petugas." : "Bukti tidak memadai.");
  const r = await fetch(API + `/api/police/validate/${id}`, { method: "POST", body: fd });
  const data = await r.json();
  toast(status === "valid"
    ? `Laporan #${id} valid. Kompensasi Rp ${data.reward.toLocaleString('id-ID')}`
    : `Laporan #${id} ditolak.`, status === "valid" ? "#22c55e" : "#ef4444");
  loadPolice();
  loadStats();
}

// ===== Riwayat =====
async function loadFeed() {
  const st = document.getElementById("filter-status").value;
  const r = await fetch(API + "/api/reports" + (st ? "?status=" + st : ""));
  const list = await r.json();
  const el = document.getElementById("feed-list");
  if (!list.length) { el.innerHTML = '<div class="card"><p class="hint">Belum ada laporan.</p></div>'; return; }
  el.innerHTML = list.map(rep => `
    <div class="report ${rep.status}">
      <div class="row">
        <img class="thumb" src="/uploads/${rep.photo_path}" alt="bukti">
        <div class="meta">
          <strong>#${rep.id} — ${labelOf(rep.violation_type)}</strong><br>
          Plat: ${rep.plate_number || "-"} · ${rep.created_at?.slice(0,16).replace("T"," ")}<br>
          <span class="status-tag">${rep.status}</span>
          ${rep.status === "valid"
            ? `<span style="color:#22c55e; font-weight:600; margin-left:8px;">
                 Kompensasi Rp ${rep.reward_amount.toLocaleString('id-ID')}</span>` : ""}
        </div>
      </div>
    </div>
  `).join("");
}

function labelOf(t) {
  return { helmet: "Tanpa Helm", wrong_way: "Melawan Arus", red_light: "Lampu Merah" }[t] || t;
}

document.getElementById("filter-status").onchange = loadFeed;

// ===== Init =====
loadStats();