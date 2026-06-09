# ⚡ Auditoria Automática de Projetos Elétricos

Sistema desenvolvido para automatizar a análise de projetos elétricos em PDF, realizando extração inteligente de informações técnicas, associação de elementos da planta e geração automática de planilhas Excel para auditoria.

---

## 🚀 Sobre o Projeto

O objetivo deste sistema é reduzir o tempo gasto na conferência manual de projetos elétricos, automatizando a identificação e organização de informações presentes em plantas técnicas.

O fluxo realiza:

- Leitura de arquivos PDF
- Conversão das páginas para imagem
- OCR para extração de textos
- Detecção de postes e vãos
- Associação de informações através de análise espacial
- Correção automática de textos OCR
- Cálculo de confiança dos dados extraídos
- Exportação para Excel
- Histórico de processamento

---

## 📷 Fluxo de Processamento

```text
PDF
 ↓
Conversão para Imagem
 ↓
OCR
 ↓
Detecção de Elementos
 ↓
Associação de Informações
 ↓
Validação
 ↓
Excel Final
