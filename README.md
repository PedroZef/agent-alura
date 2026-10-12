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
  Pergunta do Colaborador                     | Top-6 Chunks Relevantes
           |                                  v
           v                          +-------------------------------+
 +---------------------+               |     Motor RAG (Gemini)        |
 |  Interface Web      | ------------> |   (modules/rag_engine.py)     |
 |   (Streamlit)       | <------------ |  - Busca vetorial por query   |
 +---------------------+  Resposta +   |  - Prompt com Síntese RAG     |
           |              Fontes       |  - Fallback resiliente de LLM |
           v                          +-------------------------------+
 +---------------------+
 | Painel de Feedback  |
 |(feedback_logs.json) |
 +---------------------+
```

### Principais Pilares da Arquitetura:
1. **Ingestão Inteligente (`modules/ingestion.py`)**: Extração de texto de documentos PDF, Word, planilhas Excel/CSV, apresentações PowerPoint, Markdown, HTML e JSON. O texto é fatiado em blocos (*chunks*) com sobreposição (*overlap*) para preservar o contexto semântico.
2. **Indexação Vetorial (`ChromaDB`)**: Cada bloco recebe um embedding gerado pela API Google Gemini (`gemini-embedding-001`) e é armazenado com metadados (arquivo de origem, categoria e índice do chunk).
3. **Recuperação e Síntese Contextual (`modules/rag_engine.py`)**: A pergunta do usuário é convertida em vetor, os trechos mais relevantes são recuperados (Top-6) e injetados em um prompt contextual. O modelo correlaciona informações distribuídas entre diferentes documentos e mantém proteção anti-alucinação estrita.
4. **Interface Web com Controles no Navegador (`app.py`)**: Interface conversacional moderna desenvolvida em Streamlit com:
   * **Métricas de Avaliação em Tempo Real**: Contadores de feedback positivo (👍) e negativo (👎).
   * **Limpar Histórico do Chat**: Botão na barra lateral para resetar a conversa da sessão atual.
   * **Ocultar Mensagens no Navegador**: Interruptor na barra lateral para esconder ou exibir o histórico de mensagens sem apagar a sessão.
   * **Rodapé de Autoria**: Assinatura `@2026 - Pedro Zeferino da Silva.` presente na barra lateral e fixada no rodapé da página.

---

## 🛠️ Tecnologias e Ferramentas Utilizadas

| Componente | Tecnologia | Finalidade |
| :--- | :--- | :--- |
| **Linguagem** | Python 3.10+ | Linguagem base do projeto |
| **Interface de Usuário** | [Streamlit](https://streamlit.io/) | Frontend conversacional web com controles de sessão |
| **Modelos de Linguagem** | [Google GenAI SDK](https://ai.google.dev/) (Gemini) | Modelos responsivos e resilientes (`gemini-3.1-flash-lite`, `gemini-3.5-flash-lite`, `gemini-3.8-flash`) |
| **Embeddings** | `gemini-embedding-001` | Conversão de texto e perguntas em representação vetorial (3072 dimensões) |
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
│   ├── legal/
│   │   └── nda_contrato_sigilo.docx    # Acordo de confidencialidade da auFOOD
│   ├── operacional/
│   │   ├── onboarding_devs.pptx        # Guia de boas-vindas e stack técnica
│   │   └── Demanda-de-Talentos-em-TIC.pdf # Relatório setorial completo da Brasscom
│   ├── financeiro/
│   │   ├── analise_brasscom_estrategia.md # Posicionamento estratégico e contratação
│   │   └── Relatorio_Brasscom_Demanda_Talentos_TIC.xlsx # Dados quantitativos da Brasscom
│   └── EdTech/
│       ├── Brasscom_Alura.docx         # Comparativo e sinergia institucional Brasscom x Alura
│       └── Alura Cursos Online.html    # Catálogo de cursos e trilhas de formação
├── modules/
│   ├── ingestion.py                    # Script de extração, chunking e indexação no ChromaDB
│   └── rag_engine.py                   # Mecanismo de busca vetorial e geração com Gemini
├── app.py                              # Interface gráfica Streamlit com controles de histórico
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
Para indexar todos os documentos da pasta `data/` dentro do ChromaDB:
```bash
python modules/ingestion.py
```

### 6. Iniciar a Aplicação Web
```bash
streamlit run app.py
```
Acesse o navegador no endereço indicado (normalmente `http://localhost:8501`).

---

## 💡 Exemplos de Perguntas e Respostas Geradas pelo Agente

Abaixo estão exemplos reais testados no assistente demonstrando respostas mono-documentais, cruzamentos multidocumentais e tratamento anti-alucinação:

### Exemplo 1: Dúvida sobre Código de Conduta e RH (Fonte: PDF)
* **Pergunta do Colaborador:**
  > *"O que o código de conduta diz sobre conflito de interesses e atividades paralelas?"*
* **Resposta do Agente:**
  > De acordo com o Código de Conduta da SERIS, o documento estabelece as seguintes diretrizes sobre conflitos de interesse:
  > - **Objetivo:** O Código visa evitar conflitos entre os anseios individuais dos colaboradores e os objetivos empresariais da SERIS.
  > - **Atividades paralelas:** Não é permitido aceitar cargos ou funções em outras empresas ou entidades em horários conflitantes com o expediente na SERIS. Exceções são admitidas apenas em casos especiais, com registro no RH.
  > - **Procedimento em caso de dúvida:** O colaborador deve consultar sua liderança imediata ou a área de Recursos Humanos.
  >
  > 📚 **Fontes consultadas:** `Codigo-de-Conduta-SERIS.pdf (rh)`

---

### Exemplo 2: Dúvida sobre Confidencialidade e NDA (Fonte: DOCX)
* **Pergunta do Colaborador:**
  > *"Quais ativos de tecnologia e dados o colaborador do auFOOD é obrigado a manter em sigilo absoluto?"*
* **Resposta do Agente:**
  > De acordo com o Contrato de Confidencialidade (NDA) do auFOOD, todos os colaboradores, incluindo desenvolvedores e engenheiros de dados, comprometem-se a manter sigilo absoluto sobre:
  > 1. Os algoritmos de recomendação do auFOOD;
  > 2. A estrutura do banco de dados vetorial;
  > 3. Os relatórios estratégicos da Brasscom utilizados internamente.
  > 
  > Além disso, o documento estipula que o vazamento de informações da arquitetura na nuvem (OCI) resultará em rescisão imediata do contrato.
  >
  > 📚 **Fontes consultadas:** `nda_contrato_sigilo.docx (legal)`

---

### Exemplo 3: EdTech e Formação em Inteligência Artificial (Fontes: DOCX, PPTX e Markdown)
* **Pergunta do Colaborador:**
  > *"De que maneira a Alura prepara profissionais para atuar nas áreas de Inteligência Artificial e Ciência de Dados e como isso se conecta à nossa empresa?"*
* **Resposta do Agente:**
  > A Alura atua como uma escola online focada na capacitação prática para carreiras em tecnologia, oferecendo cursos e trilhas dedicadas especificamente às áreas de **Inteligência Artificial, Ciência de Dados, Programação e Inovação** (`Brasscom_Alura.docx`).
  > 
  > Para a **auFOOD**, essa atuação é estratégica:
  > - **Alinhamento com a Stack de IA:** Nossos times utilizam ferramentas modernas de Inteligência Artificial, como **LangChain e Google Gemini** (`onboarding_devs.pptx`), exigindo conhecimento prático em engenharia de dados e LLMs.
  > - **Desenvolvimento Interno de Talentos:** A capacitação contínua via Alura viabiliza a diretriz da auFOOD de treinar desenvolvedores juniores e plenos em tecnologias full-stack e IA, mitigando os custos de contratação no mercado e superando o apagão de talentos de TIC (`analise_brasscom_estrategia.md`).
  >
  > 📚 **Fontes consultadas:**
  > - `Brasscom_Alura.docx (EdTech)`
  > - `onboarding_devs.pptx (operacional)`
  > - `analise_brasscom_estrategia.md (financeiro)`

---

### Exemplo 4: Cruzamento Multidocumental Complexo (Estratégia + Mercado + Capacitação)
* **Pergunta do Colaborador:**
  > *"Com base no apagão de talentos de TIC e na meta de formar desenvolvedores em casa, de que forma as soluções da Alura auxiliam a auFOOD a superar esse déficit?"*
* **Resposta do Agente:**
  > Para superar o déficit de talentos projetado pela Brasscom e apoiar a nova estratégia de contratação da auFOOD, a capacitação através da Alura funciona como pilar central de sustentação:
  > 
  > 1. **Resposta ao Cenário de Mercado:** O relatório da Brasscom aponta que o Brasil demanda centenas de milhares de profissionais enquanto o ensino superior tradicional forma uma fração dessa necessidade. Diante do encarecimento de seniores, a auFOOD reestruturou seu recrutamento para focar em profissionais juniores e plenos.
  > 2. **O Papel da Alura na Formação Contínua:** A Alura fornece a infraestrutura educacional necessária para acelerar o desenvolvimento desses colaboradores em programação, dados e inteligência artificial, preparando-os para operar nossa stack (React, Vite, Supabase, LangChain e Gemini).
  > 3. **Conformidade e Sigilo:** O desenvolvimento profissional ocorre respeitando estritamente o NDA corporativo, garantindo que algoritmos internos e bancos vetoriais permaneçam confidenciais.
  >
  > 📚 **Fontes consultadas:**
  > - `analise_brasscom_estrategia.md (financeiro)`
  > - `Brasscom_Alura.docx (EdTech)`
  > - `onboarding_devs.pptx (operacional)`
  > - `nda_contrato_sigilo.docx (legal)`

---

### Exemplo 5: Prevenção Anti-Alucinação (Informação Ausente nos Documentos)
* **Pergunta do Colaborador:**
  > *"Qual é a política de reembolso para viagens internacionais de férias?"*
* **Resposta do Agente:**
  > Não encontrei essa informação na documentação interna disponível.  
  > *(O assistente recusa-se a inventar procedimentos ou políticas não documentadas).*

---

## 🎛️ Recursos da Interface Web (`app.py`)

A interface foi enriquecida com controles para gerenciar a experiência do usuário diretamente no navegador:

* **🗑️ Botão Limpar Histórico do Chat**: Localizado na barra lateral, permite ao usuário resetar instantaneamente todas as mensagens da sessão atual com um clique.
* **👁️ Interruptor Ocultar Mensagens no Navegador**: Permite ocultar visualmente as perguntas e respostas na tela sem apagar os dados da memória de sessão.
* **👍 / 👎 Painel de Avaliações**: Cada resposta do assistente conta com botões de avaliação que alimentam as métricas em tempo real e gravam logs de auditoria em `feedback_logs.json`.
* **🏷️ Rodapé de Autoria**: Identificação `@2026 - Pedro Zeferino da Silva.` presente na barra lateral e fixada na parte inferior da tela principal.

---

## 📝 Licença e Direitos

Projeto desenvolvido para fins educacionais e corporativos.  
Distribuído sob a licença **MIT**. Veja o arquivo [`LICENSE`](LICENSE) para mais detalhes.

© 2026 - Pedro Zeferino da Silva.
