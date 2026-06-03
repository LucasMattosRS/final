// ── Upload e polling de status ────────────────────────────────────────────────

async function enviarPDF() {
    const arquivo = document.getElementById("fileInput").files[0];
    const status  = document.getElementById("status");
    const barra   = document.getElementById("barra");

    status.innerHTML = "";

    if (!arquivo) {
        status.innerHTML = '<div class="alert alert-warning">Selecione um PDF.</div>';
        return;
    }

    // Bloqueia o botao durante o processamento
    const btn = document.getElementById("btnProcessar");
    btn.disabled = true;
    btn.innerText = "Aguarde...";

    const formData = new FormData();
    formData.append("file", arquivo);

    setBarra(10, "Enviando...");

    try {
        // 1. Envia o PDF e recebe o job_id
        const respUpload = await fetch("/upload", { method: "POST", body: formData });
        const dadosUpload = await respUpload.json();

        if (!respUpload.ok || !dadosUpload.success) {
            mostrarErro(dadosUpload.error || "Erro ao enviar o PDF.");
            resetarBotao(btn);
            return;
        }

        setBarra(20, "Processando...");

        // 2. Polling: consulta /status/:job_id ate concluir
        await aguardarJob(dadosUpload.job_id, btn, status, barra);

    } catch (error) {
        setBarra(0, "0%");
        mostrarErro("Falha de rede: " + error.message);
        resetarBotao(btn);
    }
}


async function aguardarJob(jobId, btn, status, barra) {
    const INTERVALO_MS = 2000;   // consulta a cada 2 segundos
    let progresso = 20;

    while (true) {
        await esperar(INTERVALO_MS);

        let resp, dados;
        try {
            resp  = await fetch("/status/" + jobId);
            dados = await resp.json();
        } catch (e) {
            mostrarErro("Erro ao consultar status: " + e.message);
            resetarBotao(btn);
            return;
        }

        if (dados.status === "processando" || dados.status === "aguardando") {
            // Avanca barra suavemente ate 90%
            progresso = Math.min(progresso + 8, 90);
            setBarra(progresso, "Processando... " + progresso + "%");
            continue;
        }

        if (dados.status === "concluido") {
            setBarra(100, "100%");
            status.innerHTML =
                `<div class="alert alert-success">
                    Processado com sucesso!
                    <a href="/download/${dados.excel}" class="btn btn-success ms-3">
                        <i class="bi bi-file-earmark-excel"></i> Baixar Excel
                    </a>
                </div>`;
            resetarBotao(btn);
            carregarHistorico();
            return;
        }

        if (dados.status === "erro") {
            setBarra(0, "0%");
            mostrarErro(dados.error || "Erro desconhecido durante o processamento.");
            // Mostra log tecnico em detalhes colapsavel
            if (dados.log) {
                status.innerHTML +=
                    `<details class="mt-2">
                        <summary class="text-muted" style="cursor:pointer">Ver log tecnico</summary>
                        <pre class="bg-dark text-light p-2 mt-1" style="font-size:0.75rem;max-height:200px;overflow:auto">${escaparHTML(dados.log)}</pre>
                    </details>`;
            }
            resetarBotao(btn);
            return;
        }
    }
}


// ── Historico ─────────────────────────────────────────────────────────────────

async function carregarHistorico() {
    const tabela = document.getElementById("historico");
    if (!tabela) return;

    try {
        const resposta = await fetch("/api/historico");
        const dados    = await resposta.json();

        tabela.innerHTML = "";
        dados.slice().reverse().forEach(item => {
            tabela.innerHTML +=
                `<tr>
                    <td>${item.pdf}</td>
                    <td>${item.excel}</td>
                    <td>${item.data}</td>
                    <td>
                        <a class="btn btn-success btn-sm" href="/download/${item.excel}">
                            <i class="bi bi-download"></i> Download
                        </a>
                    </td>
                </tr>`;
        });

        if (dados.length === 0) {
            tabela.innerHTML = '<tr><td colspan="4" class="text-center text-muted">Nenhum arquivo processado ainda.</td></tr>';
        }
    } catch (e) {
        console.error("Erro ao carregar historico:", e);
    }
}


// ── Helpers ───────────────────────────────────────────────────────────────────

function setBarra(pct, texto) {
    const barra = document.getElementById("barra");
    if (!barra) return;
    barra.style.width  = pct + "%";
    barra.innerText    = texto || pct + "%";
}

function mostrarErro(msg) {
    const status = document.getElementById("status");
    if (status) status.innerHTML = `<div class="alert alert-danger">${msg}</div>`;
}

function resetarBotao(btn) {
    if (!btn) return;
    btn.disabled  = false;
    btn.innerText = "Processar";
}

function esperar(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

function escaparHTML(str) {
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
}

// Carrega historico ao abrir qualquer pagina que tenha a tabela
carregarHistorico();
