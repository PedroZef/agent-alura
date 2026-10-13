import os
import chromadb  # pyright: ignore[reportMissingImports]
from google import genai
from dotenv import load_dotenv  # pyright: ignore[reportMissingImports]

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROMA_DATA_PATH = os.path.join(BASE_DIR, "chroma_db")

api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError(
        "Chave de API não encontrada. Defina GEMINI_API_KEY ou GOOGLE_API_KEY no arquivo .env."
    )

genai_client = genai.Client(api_key=api_key)
client = chromadb.PersistentClient(path=CHROMA_DATA_PATH)
collection = client.get_or_create_collection(name="documentos_empresa")


CANDIDATE_MODELS = [
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash-lite",
    "gemini-3.8-flash",
    "gemini-3.5-flash",
    "gemini-flash-latest",
]


def call_gemini(prompt: str) -> str:
    last_err = None
    for model_name in CANDIDATE_MODELS:
        try:
            response = genai_client.models.generate_content(
                model=model_name, contents=prompt
            )
            if response and response.text:
                return response.text.strip()
        except Exception as e:
            last_err = e
            continue
    if last_err:
        raise last_err
    return ""


def get_query_embedding(query: str) -> list[float]:
    response = genai_client.models.embed_content(
        model="gemini-embedding-001",
        contents=query,
        config={"task_type": "RETRIEVAL_QUERY"},
    )
    return response.embeddings[0].values


def is_external_knowledge_helpful(user_query: str) -> bool:
    """
    Decisão da arquitetura (docs/RAG.png):
    Avalia se a mensagem precisa de busca na base documental corporativa.
    """
    prompt = f"""Você é o roteador de intenções de um assistente corporativo interno.
Analise a mensagem do usuário e determine se ela necessita de consulta à documentação interna da empresa (código de conduta, RH, NDA, regras, capacitação, relatórios, contratos, stack técnica).

Mensagem do usuário: "{user_query}"

Regras:
- Se for apenas saudação ('olá', 'boa tarde'), agradecimento, despedida ou conversa informal, responda: NAO
- Se solicitar informações sobre a empresa, políticas, diretrizes, códigos, processos ou dados técnicos/financeiros, responda: SIM

Responda APENAS com a palavra 'SIM' ou 'NAO'."""
    try:
        decision = call_gemini(prompt).upper()
        return "SIM" in decision
    except Exception:
        return True


def generate_search_queries(user_query: str, missing_aspect: str = "") -> list[str]:
    """
    Passo da arquitetura (docs/RAG.png): 'Generate query(ies)'
    Gera query(ies) otimizadas para busca vetorial no ChromaDB.
    """
    if missing_aspect:
        prompt = f"""A pergunta original do colaborador é: "{user_query}"
Na busca anterior faltaram dados sobre: "{missing_aspect}".
Gere exatamente 1 query concisa e direta para busca vetorial focada nesse aspecto faltante.
Responda apenas com o texto da query."""
    else:
        prompt = f"""O colaborador fez a seguinte pergunta: "{user_query}"
Gere 1 ou 2 queries concisas de busca semântica, removendo saudações e focando nas palavras-chave mais relevantes (ex: código de conduta, conflito de interesses, horas de trabalho, etc.).
Escreva uma query por linha, sem numeração ou marcadores."""

    try:
        text = call_gemini(prompt)
        queries = [q.strip('- *"\t ') for q in text.split("\n") if q.strip()]
        return queries[:2] if queries else [user_query]
    except Exception:
        return [user_query]


def retrieve_from_chroma(queries: list[str], top_k: int = 4) -> tuple[str, list[str]]:
    """
    Passo da arquitetura (docs/RAG.png): 'Query' -> 'Embedding model' -> 'Database' -> 'Context'
    """
    seen_ids = set()
    context_parts = []
    sources = []

    for q in queries:
        try:
            q_emb = get_query_embedding(q)
            results = collection.query(query_embeddings=[q_emb], n_results=top_k)
            docs = results.get("documents", [[]])[0]
            metas = results.get("metadatas", [[]])[0]
            ids = results.get("ids", [[]])[0]

            for doc_id, doc, meta in zip(ids, docs, metas):
                if doc_id not in seen_ids:
                    seen_ids.add(doc_id)
                    source_name = f"{meta['source']} ({meta['category']})"
                    sources.append(source_name)
                    context_parts.append(f"\n--- Documento: {source_name} ---\n{doc}\n")
        except Exception as e:
            print(f"Erro ao buscar '{q}' no ChromaDB: {e}")

    return "".join(context_parts), list(dict.fromkeys(sources))


def check_requires_more_search(
    user_query: str, current_context: str
) -> tuple[bool, str]:
    """
    Decisão da arquitetura (docs/RAG.png): 'Requires more search?'
    Avalia se o contexto recuperado é suficiente ou se necessita de busca complementar.
    """
    if not current_context.strip():
        return False, ""

    prompt = f"""Você é um avaliador de recuperação de informações em um sistema RAG.
Pergunta do colaborador: "{user_query}"

Contexto já recuperado:
{current_context[:1500]}

Avalie: O contexto atual já possui menções e informações suficientes para responder aos pontos principais da pergunta, ou há algum tópico essencial da pergunta completamente ausente que justificaria uma busca adicional?
Se for suficiente ou se o documento já trata do tema, responda: SUFICIENTE
Se faltar um tópico crucial, responda: BUSCAR_MAIS: [descreva brevemente o termo faltante]"""

    try:
        evaluation = call_gemini(prompt)
        if "BUSCAR_MAIS:" in evaluation:
            missing = evaluation.split("BUSCAR_MAIS:")[1].strip()
            return True, missing
        return False, ""
    except Exception:
        return False, ""


def query_rag(user_query: str, top_k: int = 5) -> dict:
    """
    Implementação completa do fluxo em tempo real definido em docs/RAG.png:
    User -> Gemini -> External knowledge helpful?
       -> Não: Gera resposta direta
       -> Sim: Gera query(ies) -> Query -> Embedding model -> Database -> Context
               Verifica 'Requires more search?' -> Refina se necessário -> Resposta Final
    """
    workflow_info = {
        "needs_external_knowledge": True,
        "generated_queries": [],
        "search_rounds": 1,
        "requires_more_search": False,
    }

    # 1. Decisão: External knowledge helpful?
    needs_knowledge = is_external_knowledge_helpful(user_query)
    workflow_info["needs_external_knowledge"] = needs_knowledge

    if not needs_knowledge:
        direct_prompt = f"""Você é o Assistente Virtual Corporativo interno da empresa.
Responda de forma cordial, prestativa e profissional à seguinte mensagem do colaborador:
"{user_query}"
"""
        direct_answer = call_gemini(direct_prompt)
        return {
            "answer": direct_answer,
            "sources": [],
            "workflow": workflow_info,
        }

    # 2. Gera queries de busca
    queries = generate_search_queries(user_query)
    workflow_info["generated_queries"] = list(queries)

    # 3. Consulta ChromaDB (Rodada 1)
    context, sources = retrieve_from_chroma(queries, top_k=top_k)

    # 4. Decisão: Requires more search?
    requires_more, missing_topic = check_requires_more_search(user_query, context)
    if requires_more and missing_topic:
        workflow_info["requires_more_search"] = True
        workflow_info["search_rounds"] = 2
        extra_queries = generate_search_queries(
            user_query, missing_aspect=missing_topic
        )
        workflow_info["generated_queries"].extend(extra_queries)
        extra_context, extra_sources = retrieve_from_chroma(extra_queries, top_k=3)
        context += extra_context
        sources = list(dict.fromkeys(sources + extra_sources))

    if not context.strip():
        return {
            "answer": "Não encontrei essa informação na documentação interna disponível.",
            "sources": [],
            "workflow": workflow_info,
        }

    # 5. Síntese final com Gemini
    final_prompt = f"""Você é o Assistente Virtual Corporativo interno da empresa.
Responda à dúvida do colaborador sintetizando e correlacionando as informações disponíveis no CONTEXTO abaixo.
Quando a pergunta relacionar mais de um tema ou documento (ex.: estratégia, capacitação, código de conduta, stack técnica), mostre claramente como as informações se complementam.
Se a informação estiver completamente ausente ou não tiver qualquer base ou menção nos documentos, declare: 'Não encontrei essa informação na documentação interna disponível.'
Sempre cite ao final os nomes dos documentos utilizados como referência.

CONTEXTO:
{context}

PERGUNTA DO COLABORADOR:
{user_query}
"""
    final_answer = call_gemini(final_prompt)

    return {
        "answer": final_answer,
        "sources": sources,
        "workflow": workflow_info,
    }
