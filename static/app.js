// ── Intake: seleção, arrastar-e-soltar, nome do arquivo ──────────────────────
(function initIntake() {
  const dz = document.getElementById("dropzone");
  const input = document.getElementById("fileInput");
  if (!dz || !input) return;

  const mostrarNome = () => {
    const alvo = document.getElementById("arquivoEscolhido");
    if (!alvo) return;
    const f = input.files[0];
    if (f) {
      alvo.querySelector("span").innerText = f.name;
      alvo.style.display = "inline-flex";
      setRotulo("Pronto: " + f.name);
    } else {
      alvo.style.display = "none";
    }
  };

  input.addEventListener("change", mostrarNome);

  ["dragenter", "dragover"].forEach(ev =>
    dz.addEventListener(ev, e => { e.preventDefault(); dz.classList.add("is-drag"); }));
  ["dragleave", "drop"].forEach(ev =>
    dz.addEventListener(ev, e => { e.preventDefault(); dz.classList.remove("is-drag"); }));
  dz.addEventListener("drop", e => {
    if (e.dataTransfer.files.length) { input.files = e.dataTransfer.files; mostrarNome(); }
  });
})();


// ── Upload e polling de status ───────────────────────────────────────────────
async function enviarPDF() {
  const arquivo = document.getElementById("fileInput").files[0];
  const status  = document.getElementById("status");
  status.innerHTML = "";

  if (!arquivo) {
    status.innerHTML = '<div class="alert alert-warning"><i class="bi bi-exclamation-triangle"></i> Escolha um PDF antes de processar.</div>';
    return;
  }

  const btn = document.getElementById("btnProcessar");
  btn.disabled = true;
  btn.innerHTML = '<i class="bi bi-hourglass-split"></i> Processando…';

  const formData = new FormData();
  formData.append("file", arquivo);

  setBarra(10, "Enviando o arquivo…");

  try {
    const respUpload = await fetch("/upload", { method: "POST", body: formData });
    const dadosUpload = await respUpload.json();

    if (!respUpload.ok || !dadosUpload.success) {
      mostrarErro(dadosUpload.error || "Não foi possível enviar o PDF.");
      resetarBotao(btn);
      return;
    }

    setBarra(20, "Lendo a planta…");
    await aguardarJob(dadosUpload.job_id, btn, status);

  } catch (error) {
    setBarra(0, "Pronto para processar");
    mostrarErro("Falha de rede: " + error.message);
    resetarBotao(btn);
  }
}


async function aguardarJob(jobId, btn, status) {
  const INTERVALO_MS = 2000;
  let progresso = 20;

  while (true) {
    await esperar(INTERVALO_MS);

    let dados;
    try {
      dados = await (await fetch("/status/" + jobId)).json();
    } catch (e) {
      mostrarErro("Erro ao consultar o status: " + e.message);
      resetarBotao(btn);
      return;
    }

    if (dados.status === "processando" || dados.status === "aguardando") {
      progresso = Math.min(progresso + 8, 90);
      setBarra(progresso, "Extraindo postes e vãos…");
      continue;
    }

    if (dados.status === "concluido") {
      setBarra(100, "Concluído");
      status.innerHTML =
        `<div class="alert alert-success">
            <i class="bi bi-check-circle-fill"></i> Auditoria concluída.
            <a href="/download/${dados.excel}" class="btn btn-success btn-sm">
              <i class="bi bi-file-earmark-excel"></i> Baixar planilha
            </a>
         </div>`;
      resetarBotao(btn);
      carregarHistorico();
      return;
    }

    if (dados.status === "erro") {
      setBarra(0, "Pronto para processar");
      mostrarErro(dados.error || "O processamento falhou.");
      if (dados.log) {
        status.innerHTML +=
          `<details class="mt-2">
              <summary class="text-muted" style="cursor:pointer">Ver log técnico</summary>
              <pre class="p-2 mt-1" style="font-size:.75rem;max-height:200px;overflow:auto">${escaparHTML(dados.log)}</pre>
           </details>`;
      }
      resetarBotao(btn);
      return;
    }
  }
}


// ── Histórico ─────────────────────────────────────────────────────────────────
async function carregarHistorico() {
  const tabela = document.getElementById("historico");
  if (!tabela) return;

  try {
    const dados = await (await fetch("/api/historico")).json();
    tabela.innerHTML = "";

    if (!dados.length) {
      tabela.innerHTML =
        '<tr><td colspan="4" class="text-center text-muted" style="padding:34px">Nenhum projeto processado ainda. Comece pela tela <b>Processar projeto</b>.</td></tr>';
      return;
    }

    dados.slice().reverse().forEach(item => {
      tabela.innerHTML +=
        `<tr>
            <td>${item.pdf}</td>
            <td>${item.excel}</td>
            <td class="text-muted">${item.data}</td>
            <td><a class="btn btn-success btn-sm" href="/download/${item.excel}"><i class="bi bi-download"></i> Baixar</a></td>
         </tr>`;
    });
  } catch (e) {
    console.error("Erro ao carregar histórico:", e);
  }
}


// ── Helpers ───────────────────────────────────────────────────────────────────
function setBarra(pct, rotulo) {
  const barra = document.getElementById("barra");
  if (barra) { barra.style.width = pct + "%"; barra.innerText = pct + "%"; }
  if (rotulo) setRotulo(rotulo);
}
function setRotulo(txt) {
  const r = document.getElementById("rotuloProgresso");
  if (r) r.innerText = txt;
}
function mostrarErro(msg) {
  const status = document.getElementById("status");
  if (status) status.innerHTML = `<div class="alert alert-danger"><i class="bi bi-x-octagon-fill"></i> ${msg}</div>`;
}
function resetarBotao(btn) {
  if (!btn) return;
  btn.disabled = false;
  btn.innerHTML = '<i class="bi bi-lightning-charge"></i> Processar';
}
function esperar(ms) { return new Promise(r => setTimeout(r, ms)); }
function escaparHTML(str) {
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

carregarHistorico();
