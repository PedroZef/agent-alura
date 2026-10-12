# 🤖 Alura Agent: Base de Conhecimento RAG com Google Gemini

O **Alura Agent** é um assistente corporativo de Inteligência Artificial baseado na arquitetura **RAG (Retrieval-Augmented Generation)**. O agente permite que colaboradores consultem políticas de Recursos Humanos, manuais de integração técnica, contratos de sigilo, relatórios de mercado e diretrizes internas em linguagem natural, recebendo respostas precisas, fundamentadas e com citação das fontes consultadas.

---

## 🏗️ Arquitetura da Solução

O sistema integra processamento multiformato de documentos, embeddings vetoriais, recuperação semântica e interface interativa com painel de auditoria:

```
                  +-------------------------------------------------------+
                  |               Pasta de Documentos (data/)             |
                  |  [PDF] [DOCX] [XLSX] [PPTX] [CSV] [JSON] [HTML] [MD]  |
                  +-------------------------------------------------------+
                                              |
                                              v
                               +-------------------------------+
                               |     Módulo de Ingestão        |
                               |   (modules/ingestion.py)      |
                               |  - Extração multiformato      |
                               |  - Chunks com sobreposição    |
                               |  - Embeddings Gemini          |
                               +-------------------------------+
                                              |
                                              v
                               +-------------------------------+
                               |   Banco Vetorial (ChromaDB)   |
                               |  - Coleção persistente local  |
                               |  - Metadados de categoria     |
                               +-------------------------------+
                                              |
  Pergunta do Colaborador                     | Top-K Chunks Relevantes
           |                                  v
           v                          +-------------------------------+
 +---------------------+               |     Motor RAG (Gemini)        |
 |  Interface Web      | ------------> |   (modules/rag_engine.py)     |
 |   (Streamlit)       | <------------ |  - Busca vetorial por query   |
 +---------------------+  Resposta +   |  - Prompt Anti-Alucinação     |
           |              Fontes       |  - Fallback resiliente de LLM |
           v                          +-------------------------------+
 +---------------------+
 | Painel de Feedback  |
 |(feedback_logs.json) |
 +---------------------+
```

### Principais Pilares da Arquitetura:
1. **Ingestão Inteligente (`modules/ingestion.py`)**: Extração de texto de documentos PDF, Word, planilhas Excel/CSV, apresentações PowerPoint, Markdown, HTML e JSON. O texto é fatiado em blocos (*chunks*) com sobreposição (*overlap*) para preservar o contexto.
2. **Indexação Vetorial (`ChromaDB`)**: Cada bloco recebe um embedding gerado pela API Google Gemini (`gemini-embedding-001`) e é armazenado com metadados (arquivo de origem, categoria e índice do chunk).
3. **Recuperação e Geração Anti-Alucinação (`modules/rag_engine.py`)**: A pergunta do usuário é convertida em vetor, os trechos mais relevantes são recuperados e injetados em um prompt estrito. O modelo é instruído a responder exclusivamente com base no contexto e citar os arquivos de referência.
4. **Interface e Auditoria (`app.py`)**: Interface conversacional moderna desenvolvida em Streamlit, incluindo métricas em tempo real de avaliações positivas/negativas e histórico persistido em `feedback_logs.json`.

---

## 🛠️ Tecnologias e Ferramentas Utilizadas

| Componente | Tecnologia | Finalidade |
| :--- | :--- | :--- |
| **Linguagem** | Python 3.10+ | Linguagem base do projeto |
| **Interface de Usuário** | [Streamlit](https://streamlit.io/) | Frontend conversacional web com painel lateral |
| **Modelos de Linguagem** | [Google GenAI SDK](https://ai.google.dev/) (Gemini) | Geração de respostas fundamentadas (`gemini-3.1-flash-lite`, `gemini-3.5-flash-lite`, `gemini-3.8-flash`) |
| **Embeddings** | `gemini-embedding-001` | Conversão de texto e perguntas em representação vetorial |
| **Banco Vetorial** | [ChromaDB](https://www.trychroma.com/) | Banco de dados vetorial local de alta performance |
| **Processamento de PDFs** | PyPDF / PyMuPDF | Extração de texto de manuais e códigos de conduta |
| **Processamento Office** | `python-docx`, `openpyxl`, `python-pptx` | Leitura de documentos Word, Excel e slides PowerPoint |
| **Manipulação de Dados** | Pandas | Processamento e formatação de planilhas e tabelas |
| **Configuração** | `python-dotenv` | Gestão segura de credenciais via variáveis de ambiente |

---

## 📁 Estrutura do Projeto

```text
agent-alura/
├── data/                               # Documentos corporativos da base de conhecimento
│   ├── rh/
│   │   └── Codigo-de-Conduta-SERIS.pdf # Código de conduta e diretrizes de RH (PDF)
│   ├── financeiro/
│   │   ├── analise_brasscom_estrategia.md
│   │   └── Relatorio_Brasscom_Demanda_Talentos_TIC.xlsx # Dados estratégicos e métricas
│   ├── legal/
│   │   └── nda_contrato_sigilo.docx    # Acordo de confidencialidade
│   ├── operacional/
│   │   └── onboarding_devs.pptx        # Guia de boas-vindas e configuração de ambiente
│   └── EdTech/
│       └── Brasscom_Alura.docx         # Relatório complementar
├── modules/
│   ├── ingestion.py                    # Script de extração, chunking e indexação no ChromaDB
│   └── rag_engine.py                   # Mecanismo de busca vetorial e geração de resposta com Gemini
├── app.py                              # Interface gráfica Streamlit e controle de feedback
├── chroma_db/                          # Diretório de persistência do banco vetorial ChromaDB
├── feedback_logs.json                  # Armazenamento em JSON de avaliações (Positivo/Negativo)
├── requirements.txt                    # Dependências do projeto
├── .env                                # Chaves de API (ignorado pelo Git)
├── .gitignore                          # Arquivos e diretórios ignorados pelo controle de versão
├── LICENSE                             # Licença MIT
└── README.md                           # Documentação completa do projeto
```

---

## 🚀 Instruções de Instalação e Execução

### Pré-requisitos
* Python 3.10 ou superior instalado.
* Chave de API do Google Gemini ([Google AI Studio](https://aistudio.google.com/)).

### 1. Clonar o Repositório
```bash
git clone https://github.com/PedroZef/agent-alura.git
cd agent-alura
```

### 2. Criar e Ativar o Ambiente Virtual
No Windows (PowerShell):
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

No Linux / macOS:
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar Dependências
```bash
pip install -r requirements.txt
```

### 4. Configurar Variáveis de Ambiente
Crie um arquivo `.env` na raiz do projeto com sua chave de API:
```env
GOOGLE_API_KEY=sua_chave_gemini_aqui
```

### 5. Executar a Ingestão dos Documentos
Para indexar os documentos presentes na pasta `data/` dentro do ChromaDB:
```bash
python modules/ingestion.py
```
> O script lerá automaticamente os arquivos `.pdf`, `.docx`, `.xlsx`, `.pptx`, `.md`, gerará os embeddings e os salvará em `chroma_db/`.

### 6. Iniciar a Aplicação Web
```bash
streamlit run app.py
```
Acesse o navegador no endereço informado (normalmente `http://localhost:8501`).

---

## 💡 Exemplos de Uso

### Exemplo 1: Dúvida sobre Código de Conduta e RH (Fonte: PDF)
* **Pergunta do Colaborador:**
  > "O que o código de conduta diz sobre conflito de interesses e atividades paralelas?"
* **Resposta do Agente:**
  > De acordo com o Código de Conduta da SERIS, o documento estabelece as seguintes diretrizes sobre conflitos de interesse:
  > - **Objetivo:** Disciplinar relacionamentos internos e externos para evitar conflitos entre interesses individuais e corporativos.
  > - **Atividades paralelas:** Não é permitido aceitar cargos ou funções em outras empresas ou entidades em horários conflitantes com o expediente na SERIS. Exceções são admitidas apenas em casos especiais com aprovação do RH.
  > - **Procedimento:** Em caso de dúvidas, o colaborador deve procurar sua liderança imediata ou a área de Recursos Humanos.
  >
  > **Documentos consultados:** `Codigo-de-Conduta-SERIS.pdf (rh)`

---

### Exemplo 2: Dúvida sobre Confidencialidade e NDA (Fonte: DOCX)
* **Pergunta do Colaborador:**
  > "Quais são as obrigações de sigilo e confidencialidade estipuladas no contrato?"
* **Resposta do Agente:**
  > As informações confidenciais compreendem dados técnicos, comerciais e estratégicos aos quais o colaborador tem acesso. O colaborador compromete-se a não divulgar, reproduzir ou utilizar tais dados para fins alheios às suas atribuições profissionais, mantendo o sigilo mesmo após o término do vínculo.
  >
  > **Documentos consultados:** `nda_contrato_sigilo.docx (legal)`

---

### Exemplo 3: Prevenção Anti-Alucinação (Informação Ausente)
* **Pergunta do Colaborador:**
  > "Qual é a política de reembolso para viagens internacionais de férias?"
* **Resposta do Agente:**
  > Não encontrei essa informação na documentação interna disponível.
  > *(O agente recusa-se a inventar procedimentos não documentados)*

---

## 📝 Licença e Direitos

Projeto desenvolvido para fins educacionais e corporativos.  
Distribuído sob a licença **MIT**. Veja o arquivo [`LICENSE`](LICENSE) para mais detalhes.

© 2026 - Pedro Zeferino da Silva.
