# Auditoria Automática de Projetos Elétricos

Sistema para análise automática de projetos elétricos em PDF, extração de informações técnicas e geração de planilhas Excel para auditoria.

## Objetivo

Automatizar a conferência de projetos elétricos, reduzindo o trabalho manual de identificação de:

- Postes
- Vãos
- Estruturas
- Condutores
- Equipamentos
- Informações associadas aos elementos da planta

O sistema processa arquivos PDF de projetos, identifica os elementos relevantes e gera planilhas Excel para auditoria e validação.

---

## Funcionalidades

### Processamento de PDFs

- Leitura automática de projetos em PDF
- Conversão das páginas em imagem
- OCR para extração de textos
- Identificação de códigos e elementos técnicos

### Detecção de Elementos

- Localização de postes
- Localização de vãos
- Identificação de estruturas
- Identificação de condutores
- Associação entre elementos e suas informações

### Auditoria

- Geração automática de Excel
- Consolidação de informações por obra
- Histórico de processamentos
- Registro de tokens não reconhecidos

### Interface Web

- Upload de arquivos PDF
- Acompanhamento do processamento
- Download automático dos arquivos Excel
- Histórico de arquivos processados

---

## Estrutura do Projeto

```text
projeto/
│
├── app.py
├── main.py
├── config.py
│
├── src/
│   ├── arrow_detector.py
│   ├── pdf_reader.py
│   ├── ocr.py
│   ├── work_number.py
│   └── ...
│
├── templates/
│   ├── index.html
│   ├── processar.html
│   ├── historico.html
│   └── configuracoes.html
│
├── static/
│
├── input_pdf/
│
├── output_excel/
│
├── logs/
│
├── dicionario.json
│
└── history.json
```

---

## Tecnologias Utilizadas

### Backend

- Python 3.11+
- Flask

### Processamento de Imagem

- OpenCV
- NumPy

### OCR

- Tesseract OCR
- pytesseract

### Manipulação de PDFs

- pdf2image
- PyMuPDF

### Planilhas

- openpyxl
- pandas

---

## Instalação

### Clonar o projeto

```bash
git clone https://github.com/seuusuario/seu-projeto.git
cd seu-projeto
```

### Criar ambiente virtual

```bash
python -m venv venv
```

Windows:

```bash
venv\Scripts\activate
```

Linux:

```bash
source venv/bin/activate
```

### Instalar dependências

```bash
pip install -r requirements.txt
```

---

## Executando

### Interface Web

```bash
python app.py
```

Acesse:

```text
http://127.0.0.1:5000
```

---

### Execução direta

```bash
python main.py
```

---

## Fluxo de Funcionamento

1. Usuário envia PDF pela interface.
2. Sistema salva o arquivo na pasta de entrada.
3. O PDF é processado.
4. O OCR extrai os textos.
5. O detector identifica elementos do projeto.
6. As informações são organizadas.
7. Um Excel é gerado automaticamente.
8. O usuário realiza o download.

---

## Logs

Os logs de processamento ficam disponíveis para facilitar depuração.

Exemplos:

```text
logs/
├── processamento.log
├── tokens_nao_reconhecidos.log
```

---

## Dicionário de OCR

O sistema possui um dicionário de termos técnicos utilizado para corrigir erros comuns do OCR.

Arquivo:

```text
dicionario.json
```

O dicionário pode ser atualizado automaticamente durante a execução.

---

## Melhorias Planejadas

### Detecção Inteligente

- Rastreamento completo das linhas de chamada
- Associação automática entre poste e informações técnicas
- Associação automática entre vão e informações técnicas
- Detecção de estruturas por visão computacional

### Inteligência Artificial

- Classificação automática de elementos
- Correção avançada de OCR
- Validação automática de inconsistências

### Interface

- Dashboard de auditoria
- Estatísticas dos projetos
- Exportação para múltiplos formatos

---

## Status do Projeto

🚧 Em desenvolvimento

Funcionalidades atuais:

- Upload de PDFs
- Processamento automático
- OCR
- Geração de Excel
- Histórico
- Correção automática de tokens

Funcionalidades em desenvolvimento:

- Rastreamento de linhas de chamada
- Associação inteligente de informações
- Auditoria visual automatizada

---

## Autor

Desenvolvido para automação de auditoria de projetos elétricos e apoio à análise técnica de redes de distribuição.
