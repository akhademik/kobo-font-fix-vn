import os
import sys
import glob
import shutil
import subprocess
import threading
import uuid
import time
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file, after_this_request
import zipfile

app = Flask(__name__)

UPLOAD_DIR = "/tmp/kobo_uploads"
OUTPUT_DIR = "/tmp/kobo_output"
SCRIPTS_DIR = "/app/scripts"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Job tracker
jobs = {}

def run_fix_job(job_id, input_dir, output_dir, win_ascent_ratio, win_descent_ratio, typo_multiplier):
    job = jobs[job_id]
    job["status"] = "running"
    job["log"] = []

    def log(msg):
        job["log"].append(msg)

    try:
        # Find TTF files
        ttf_files = [f for f in glob.glob(os.path.join(input_dir, "**", "*.ttf"), recursive=True)
                     if not os.path.basename(f).startswith(("KF_", "VN_"))]

        if not ttf_files:
            job["status"] = "error"
            job["error"] = "Không tìm thấy file .ttf nào trong thư mục đã upload."
            return

        log(f"✅ Tìm thấy {len(ttf_files)} file .ttf")

        # Step 1: kobofix
        log("\n━━━ Bước 1: kobofix (PANOSE + kern + outline + line spacing) ━━━")
        cmd = [sys.executable, os.path.join(SCRIPTS_DIR, "kobofix.py"),
               "--preset", "kf"] + ttf_files

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE,
            text=True
        )
        # Tự động trả lời "y" nếu kobofix hỏi "Continue with valid files only? [y/N]"
        try:
            proc.stdin.write("y\n")
            proc.stdin.flush()
            proc.stdin.close()
        except BrokenPipeError:
            pass

        for line in proc.stdout:
            log(line.rstrip())
        proc.wait()

        if proc.returncode != 0:
            job["status"] = "error"
            job["error"] = "kobofix thất bại."
            return

        # Kiểm tra file bị mất/gộp sau kobofix
        kf_files = glob.glob(os.path.join(input_dir, "**", "KF_*.ttf"), recursive=True)
        orig_count = len(ttf_files)
        kf_count = len(kf_files)
        log(f"\n📊 Sau kobofix: {orig_count} file gốc → {kf_count} file KF_*")
        if kf_count < orig_count:
            orig_names = {os.path.basename(f) for f in ttf_files}
            kf_names   = {os.path.basename(f) for f in kf_files}
            log(f"⚠️  Có thể {orig_count - kf_count} file bị gộp tên (kobofix đặt tên giống nhau)")
            # Tìm file gốc không có KF_ tương ứng (đã bị skip hoặc gộp)
            remaining_orig = glob.glob(os.path.join(input_dir, "**", "*.ttf"), recursive=True)
            remaining_orig = [f for f in remaining_orig if not os.path.basename(f).startswith(("KF_", "VN_"))]
            if remaining_orig:
                log(f"  File bị skip bởi kobofix ({len(remaining_orig)}):")
                for f in remaining_orig:
                    log(f"    ✗ {os.path.relpath(f, input_dir)}")

        # Step 2: fixvn with custom params — patch the script inline
        log("\n━━━ Bước 2: fixvn (WinAscent + Typo cho tiếng Việt) ━━━")

        fixvn_src = os.path.join(SCRIPTS_DIR, "fixvn.py")
        with open(fixvn_src) as f:
            code = f.read()

        # Override ratios
        code = code.replace("WIN_ASCENT_RATIO  = 1.45", f"WIN_ASCENT_RATIO  = {win_ascent_ratio}")
        code = code.replace("WIN_DESCENT_RATIO = 0.50", f"WIN_DESCENT_RATIO = {win_descent_ratio}")
        code = code.replace("int(old_typo_asc * 1.2)", f"int(old_typo_asc * {typo_multiplier})")

        tmp_fixvn = f"/tmp/fixvn_{job_id}.py"
        with open(tmp_fixvn, "w") as f:
            f.write(code)

        proc2 = subprocess.Popen(
            [sys.executable, tmp_fixvn, input_dir, output_dir],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        for line in proc2.stdout:
            log(line.rstrip())
        proc2.wait()
        os.remove(tmp_fixvn)

        if proc2.returncode != 0:
            job["status"] = "error"
            job["error"] = "fixvn thất bại."
            return

        # Tổng kết
        vn_files = glob.glob(os.path.join(output_dir, "**", "VN_*.ttf"), recursive=True)
        log(f"\n📦 Tổng kết: {len(ttf_files)} file gốc → {len(vn_files)} file output")
        if len(vn_files) < len(ttf_files):
            diff = len(ttf_files) - len(vn_files)
            log(f"⚠️  {diff} file ít hơn so với input. Nguyên nhân có thể:")
            log(f"   • File tên không chuẩn (thiếu Bold/Italic/Regular) bị kobofix skip")
            log(f"   • Nhiều file bị kobofix đặt tên giống nhau → ghi đè nhau")
            log(f"   → Xem chi tiết ở log Bước 1 phía trên")

        # Zip output
        zip_path = f"/tmp/kobo_result_{job_id}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in glob.glob(os.path.join(output_dir, "**", "*.ttf"), recursive=True):
                arcname = os.path.relpath(f, output_dir)
                zf.write(f, arcname)

        job["status"] = "done"
        job["zip_path"] = zip_path
        log(f"\n✅ Hoàn tất! File ZIP đã sẵn sàng để tải.")

    except Exception as e:
        job["status"] = "error"
        job["error"] = str(e)
        log(f"\n❌ Lỗi: {e}")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    files = request.files.getlist("fonts")
    if not files or all(f.filename == "" for f in files):
        return jsonify({"error": "Chưa chọn file"}), 400

    job_id = str(uuid.uuid4())[:8]
    input_dir = os.path.join(UPLOAD_DIR, job_id)
    output_dir = os.path.join(OUTPUT_DIR, job_id)
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    saved = 0
    paths = request.form.getlist("paths")  # relative paths gửi từ JS

    for i, f in enumerate(files):
        # Dùng relative path từ JS nếu có, fallback về tên file
        rel_path = (paths[i] if i < len(paths) else f.filename).replace("\\", "/")
        if not rel_path.lower().endswith(".ttf"):
            continue
        dest = os.path.join(input_dir, rel_path)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        f.save(dest)
        saved += 1

    if saved == 0:
        return jsonify({"error": "Không có file .ttf hợp lệ"}), 400

    win_ascent  = float(request.form.get("win_ascent", 1.45))
    win_descent = float(request.form.get("win_descent", 0.50))
    typo_mult   = float(request.form.get("typo_mult", 1.2))

    jobs[job_id] = {"status": "queued", "log": [], "zip_path": None}

    t = threading.Thread(target=run_fix_job, args=(job_id, input_dir, output_dir, win_ascent, win_descent, typo_mult))
    t.daemon = True
    t.start()

    return jsonify({"job_id": job_id, "files": saved})


@app.route("/status/<job_id>")
def status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job không tồn tại"}), 404
    return jsonify({
        "status": job["status"],
        "log": job["log"],
        "error": job.get("error"),
    })


@app.route("/download/<job_id>")
def download(job_id):
    job = jobs.get(job_id)
    if not job or job["status"] != "done":
        return jsonify({"error": "Chưa sẵn sàng"}), 404

    zip_path = job["zip_path"]
    return send_file(zip_path, as_attachment=True, download_name="kobo_fonts_vn.zip")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)