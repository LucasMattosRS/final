from flask import Flask, render_template, request, jsonify, send_file, abort
import json
import os
import subprocess
import sys
import threading
import uuid
from datetime import datetime
from config import BASE_DIR, INPUT_DIR, OUTPUT_DIR
from src.work_number import get_work_number

app = Flask(__name__)

UPLOAD_FOLDER = INPUT_DIR
OUTPUT_FOLDER = OUTPUT_DIR
HISTORY_FILE  = os.path.join(BASE_DIR, "history.json")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# ── Historico ─────────────────────────────────────────────────────────────────

def load_history() -> list[dict]:
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_history(history: list[dict]) -> None:
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


historico = load_history()

# ── Jobs em background ────────────────────────────────────────────────────────
# { job_id: { status, excel, error, log } }
_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()


def _run_job(job_id: str, nome_pdf: str) -> None:
    """Executa main.py em thread separada e atualiza o status do job."""

    def update(status, excel=None, error=None, log=""):
        with _jobs_lock:
            _jobs[job_id].update({
                "status": status,
                "excel": excel,
                "error": error,
                "log": log,
            })

    update("processando")

    try:
        result = subprocess.run(
            [sys.executable, "main.py"],
            cwd=os.path.dirname(__file__),
            capture_output=True,
            text=True,
            timeout=1800,  # 30 minutos
        )

        log_output = (
            f"RETURN CODE: {result.returncode}\n\n"
            f"STDOUT:\n{result.stdout}\n\n"
            f"STDERR:\n{result.stderr}"
        )

        if result.returncode != 0:
            error_msg = (
                result.stderr.strip()
                or result.stdout.strip()
                or "Erro desconhecido ao processar o PDF."
            )

            update(
                "erro",
                error=error_msg[:5000],
                log=log_output[:20000]
            )
            return
        

        # Procura EXCEL_GERADO no stdout
        nome_excel = None

        for line in result.stdout.splitlines():
            line = line.strip()

            if line.startswith("EXCEL_GERADO:"):
                caminho = line.split("EXCEL_GERADO:", 1)[1].strip()
                nome_excel = os.path.basename(caminho)
                break

        # Fallback
        if nome_excel is None:
            nome_excel = f"{get_work_number(nome_pdf)}.xlsx"

        caminho_excel = os.path.join(OUTPUT_FOLDER, nome_excel)

        if not os.path.exists(caminho_excel):
            update(
                "erro",
                error=f"Excel nao encontrado: {nome_excel}",
                log=log_output[:20000]
            )
            return

        entry = {
            "pdf": nome_pdf,
            "excel": nome_excel,
            "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
        }

        historico.append(entry)
        save_history(historico)

        update(
            "concluido",
            excel=nome_excel,
            log=log_output[:20000]
        )

    except subprocess.TimeoutExpired:
        update(
            "erro",
            error="Processamento excedeu 30 minutos (timeout)."
        )

    except Exception as exc:
        update(
            "erro",
            error=str(exc)
        )

# ── Rotas ─────────────────────────────────────────────────────────────────────

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/processar")
def processar():
    return render_template("processar.html")


@app.route("/configuracoes")
def configuracoes():
    return render_template("configuracoes.html")


@app.route("/upload", methods=["POST"])
def upload():
    arquivo = request.files.get("file")
    if arquivo is None:
        return jsonify({"success": False, "error": "Nenhum arquivo enviado."}), 400

    nome_pdf    = arquivo.filename
    caminho_pdf = os.path.join(UPLOAD_FOLDER, nome_pdf)
    arquivo.save(caminho_pdf)

    # Cria job e dispara em background
    job_id = str(uuid.uuid4())
    with _jobs_lock:
        _jobs[job_id] = {"status": "aguardando", "excel": None, "error": None, "log": ""}

    t = threading.Thread(target=_run_job, args=(job_id, nome_pdf), daemon=True)
    t.start()

    return jsonify({"success": True, "job_id": job_id})


@app.route("/status/<job_id>")
def status(job_id: str):
    """Frontend faz polling nesta rota ate status == concluido ou erro."""
    with _jobs_lock:
        job = _jobs.get(job_id)

    if job is None:
        return jsonify({"error": "Job nao encontrado"}), 404

    return jsonify({
        "status": job["status"],   # aguardando | processando | concluido | erro
        "excel":  job["excel"],
        "error":  job["error"],
        "log":    job["log"],
    })


@app.route("/download/<arquivo>")
def download(arquivo: str):
    caminho = os.path.normpath(os.path.join(OUTPUT_FOLDER, arquivo))
    if not caminho.startswith(os.path.abspath(OUTPUT_FOLDER)):
        abort(400, description="Nome de arquivo invalido")
    if not os.path.exists(caminho):
        abort(404, description="Arquivo nao encontrado")
    return send_file(caminho, as_attachment=True)


@app.route("/historico")
def listar():
    return render_template("historico.html")


@app.route("/api/historico")
def historico_api():
    return jsonify(historico)


if __name__ == "__main__":
    app.run(debug=True)
