# Plano de Precisão — guia rápido

Quatro frentes para aumentar a precisão do sistema, da mais barata à de maior teto.
Tudo é decidido **com número**, usando o conjunto de medição (item 3).

## A ordem certa de uso

1. **Meça o estado atual**
   ```
   python -m precisao.rodar
   ```
   Gera `precisao/saida_atual.csv` e imprime: taxa de preenchimento por coluna,
   fragmentos/grudados, confiança média. (Para testar rápido: `python -m precisao.rodar 8` = só 8 obras.)

2. **Crie o gabarito** (a verdade conferida à mão)
   ```
   python -m precisao.gabarito
   ```
   Gera `precisao/gabarito.csv` com obra/folha/código já preenchidos. Você abre,
   preenche as colunas de valor (logradouro, ancoragem, lado_forte, metragem,
   material, altura_poste) com o valor **correto** lido da planta e salva. O que
   não conseguir conferir, deixe em branco (é ignorado).

3. **Meça o acerto real**
   ```
   python -m precisao.medir
   ```
   Mostra o % de acerto por coluna e os primeiros erros de cada uma. Esse número
   é a sua bússola: toda mudança daqui pra frente é avaliada por ele.

## As quatro alavancas

### Item 1 — Tokens mais limpos (feito)
O segmentador em `src/auto_correct.py` foi corrigido: não fatia mais `112,5KVA`
em `1` + `12,5KVA`. Resultado: "Informações" mais legível e correção automática
melhor. Ganho de legibilidade/auditoria; pouco efeito nas taxas de preenchimento,
porque os parsers de material/altura já achavam o código dentro do blob.

### Item 2 — Associação seta→texto (ferramenta pronta)
O parâmetro fica em `config.py` → `ASSOCIATION_RADIUS`. Para escolher o melhor
valor **com base no acerto** (e não em encher de valor errado):
```
python -m precisao.varrer_raio 60,90,120 3
```
Roda o pipeline em 3 obras para cada raio e mostra preenchimento + acerto contra
o gabarito. Escolha o raio de **maior acerto**. (É lento; use poucas obras já
rotuladas.)

### Item 3 — Medição (feito)
É o `precisao/` inteiro: `rodar.py`, `gabarito.py`, `medir.py`. É o que torna
todo o resto mensurável.

### Item 4 — Insumo estruturado (teto de precisão)
Se o CAD/sistema da distribuidora exportar planilha (CSV/XLSX), use
`src/structured_reader.py` para gerar o Excel **sem OCR** — precisão ~100%:
```python
from src.structured_reader import importar_estruturado
from src.excel_exporter import export_excel
export_excel(importar_estruturado("export_obra.xlsx"), "saida.xlsx")
```
Os nomes de coluna são flexíveis (Rua/Logradouro/Endereço → logradouro, etc.);
veja `MAPA_COLUNAS` no arquivo. Colunas ausentes viram vazio.

## Onde colocar os arquivos
- `src/auto_correct.py`, `src/structured_reader.py` → dentro de `src/`
- pasta `precisao/` inteira → na raiz do projeto (ao lado de `main.py`)
