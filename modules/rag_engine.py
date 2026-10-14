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

try:
    from modules.sources_catalog import get_source_metadata, format_sources_for_prompt
except ModuleNotFoundError:
    from sources_catalog import get_source_metadata, format_sources_for_prompt

import time

CANDIDATE_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-flash-lite-latest",
    "gemini-3.8-flash",
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
    "gemini-flash-latest",
]


def call_gemini(prompt: str, max_retries: int = 3) -> str:
    last_err = None
    for model_name in CANDIDATE_MODELS:
        for attempt in range(max_retries):
            try:
                response = genai_client.models.generate_content(
                    model=model_name, contents=prompt
                )
                if response and response.text:
                    return response.text.strip()
            except Exception as e:
                last_err = e
                err_str = str(e)
                # Erros transitórios de taxa limite, quota ou instabilidade de servidor
                if any(x in err_str for x in ["429", "RESOURCE_EXHAUSTED", "quota", "503", "UNAVAILABLE", "500", "INTERNAL"]):
                    time.sleep(1.5 * (attempt + 1))
                    continue
                else:
                    # Modelos descontinuados ou 404: avança imediatamente para o próximo modelo candidato
                    break
    if last_err:
        raise last_err
    return ""


def get_query_embedding(query: str, max_retries: int = 4) -> list[float]:
    for attempt in range(max_retries):
        try:
            response = genai_client.models.embed_content(
                model="gemini-embedding-001",
                contents=query,
                config={"task_type": "RETRIEVAL_QUERY"},
            )
            return response.embeddings[0].values
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower():
                wait_time = (attempt + 1) * 3
                time.sleep(wait_time)
            else:
                if attempt == max_retries - 1:
                    raise e
                time.sleep(2)
    return []


import json


def route_and_generate_queries(user_query: str) -> tuple[bool, list[str]]:
    """
    Otimização de Tokens e Latência (1 chamada estruturada via JSON):
    Unifica a decisão de 'External knowledge helpful?' e a geração de queries semânticas.
    Reduz em ~50% as chamadas iniciais ao Gemini.
    """
    prompt = f"""Você é o roteador de intenções e gerador de queries de um assistente corporativo interno.
Analise a mensagem do colaborador e responda ESTRITAMENTE em formato JSON com o seguinte schema:
{{
  "needs_external_knowledge": true ou false,
  "queries": ["query semântica 1", "query semântica 2", "query semântica 3"]
}}

Regras:
1. "needs_external_knowledge":
   - false: se for apenas saudação ('olá', 'boa tarde'), agradecimento, despedida ou conversa informal.
   - true: se for sobre políticas, normas, RH, conduta, contratos, tecnologia, finanças, mercado, cursos ou processos da empresa.
2. "queries":
   - Se needs_external_knowledge for false, retorne lista vazia [].
   - Se for true, gere de 2 a 3 queries concisas e desmembradas. Se a pergunta envolver mais de um tema (ex: Brasscom/apagão de talentos E capacitação/Alura E formação interna/auFOOD), gere queries separadas para cada tema chave (ex: uma focada em 'apagão talentos Brasscom déficit', outra em 'capacitação Alura formação desenvolvedores', outra em 'estratégia auFOOD contratar formar casa').

Mensagem do colaborador: "{user_query}"
"""
    try:
        response_text = call_gemini(prompt)
        cleaned = response_text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        data = json.loads(cleaned)
        needs_knowledge = bool(data.get("needs_external_knowledge", True))
        queries = [str(q).strip() for q in data.get("queries", []) if str(q).strip()]
        if needs_knowledge and not queries:
            queries = [user_query]
        return needs_knowledge, queries[:3]
    except Exception:
        # Fallback seguro caso haja erro na formatação do JSON
        return True, [user_query]


def generate_refinement_query(user_query: str, missing_aspect: str) -> list[str]:
    """
    Gera query de busca focada em aspecto complementar pendente.
    """
    prompt = f"""A pergunta original do colaborador é: "{user_query}"
Na busca anterior faltaram dados sobre: "{missing_aspect}".
Gere exatamente 1 query concisa e direta para busca vetorial focada nesse aspecto faltante.
Responda apenas com o texto da query."""
    try:
        text = call_gemini(prompt)
        q = text.strip('- *"\t \n')
        return [q] if q else [missing_aspect]
    except Exception:
        return [missing_aspect]


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
            if not q_emb:
                print(f"Aviso: Não foi possível gerar embedding para a query '{q}'")
                continue

            # Garante que não pede mais resultados do que o total disponível
            count = collection.count()
            if count == 0:
                print("Aviso: A coleção do ChromaDB está vazia.")
                return "", []

            effective_top_k = min(top_k, count)
            results = collection.query(query_embeddings=[q_emb], n_results=effective_top_k)

            docs_list = results.get("documents") or []
            metas_list = results.get("metadatas") or []
            ids_list = results.get("ids") or []

            docs = docs_list[0] if docs_list else []
            metas = metas_list[0] if metas_list else []
            ids = ids_list[0] if ids_list else []

            for doc_id, doc, meta in zip(ids, docs, metas):
                if doc_id not in seen_ids:
                    seen_ids.add(doc_id)
                    source_name = f"{meta.get('source', 'documento')} ({meta.get('category', 'geral')})"
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

    # 1. Decisão Unificada: External knowledge helpful? + Generate query(ies)
    needs_knowledge, queries = route_and_generate_queries(user_query)
    workflow_info["needs_external_knowledge"] = needs_knowledge
    workflow_info["generated_queries"] = list(queries)

    if not needs_knowledge:
        direct_prompt = f"""Você é o Assistente Virtual Corporativo interno da empresa.
Responda de forma cordial, prestativa e profissional à seguinte mensagem do colaborador:
"{user_query}"
"""
        direct_answer = call_gemini(direct_prompt)
        return {
            "answer": direct_answer,
            "sources": [],
            "sources_metadata": [],
            "workflow": workflow_info,
        }

    # 2. Consulta ChromaDB (Rodada 1)
    context, sources = retrieve_from_chroma(queries, top_k=top_k)

    # 3. Decisão: Requires more search?
    requires_more, missing_topic = check_requires_more_search(user_query, context)
    if requires_more and missing_topic:
        workflow_info["requires_more_search"] = True
        workflow_info["search_rounds"] = 2
        extra_queries = generate_refinement_query(
            user_query, missing_aspect=missing_topic
        )
        workflow_info["generated_queries"].extend(extra_queries)
        extra_context, extra_sources = retrieve_from_chroma(extra_queries, top_k=3)
        context += extra_context
        sources = list(dict.fromkeys(sources + extra_sources))

    sources_metadata = [get_source_metadata(s) for s in sources]

    if not context.strip():
        return {
            "answer": "Não encontrei essa informação na documentação interna disponível.",
            "sources": [],
            "sources_metadata": [],
            "workflow": workflow_info,
        }

    formatted_sources_refs = format_sources_for_prompt(sources_metadata)

    # 5. Síntese final com Gemini
    final_prompt = f"""Você é o Assistente Virtual Corporativo interno da empresa.
Responda à dúvida do colaborador sintetizando e correlacionando as informações disponíveis no CONTEXTO abaixo.
Orientações:
- Quando a pergunta envolver mais de um tema (ex.: apagão de talentos, estratégia da empresa de formar internamente, soluções da Alura de capacitação), conecte os pontos e explique como os documentos se complementam.
- Se houver informações relevantes sobre parte dos tópicos no contexto (ex.: dados da Brasscom sobre apagão, estratégia da empresa de formar desenvolvedores em casa, e cursos da Alura), apresente a síntese clara desses pontos com base nos documentos.
- Somente declare que 'Não encontrei essa informação na documentação interna disponível' se o assunto da pergunta não tiver nenhuma relação ou menção em nenhum documento do contexto.
- Ao citar as referências ou ao final da resposta, inclua links Markdown clicáveis [Nome do Documento ou Portal](URL) sempre que houver links disponíveis na lista abaixo, facilitando o acesso direto do colaborador.

DOCUMENTOS E LINKS OFICIAIS DISPONÍVEIS:
{formatted_sources_refs}

CONTEXTO:
{context}

PERGUNTA DO COLABORADOR:
{user_query}
"""
    final_answer = call_gemini(final_prompt)

    return {
        "answer": final_answer,
        "sources": sources,
        "sources_metadata": sources_metadata,
        "workflow": workflow_info,
    }
