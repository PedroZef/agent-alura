import os
import chromadb
from google import genai
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROMA_DATA_PATH = os.path.join(BASE_DIR, "chroma_db")

api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("Chave de API não encontrada. Defina GEMINI_API_KEY ou GOOGLE_API_KEY no arquivo .env.")

genai_client = genai.Client(api_key=api_key)
client = chromadb.PersistentClient(path=CHROMA_DATA_PATH)
collection = client.get_or_create_collection(name="documentos_empresa")

def get_query_embedding(query: str) -> list[float]:
    response = genai_client.models.embed_content(
        model="gemini-embedding-001",
        contents=query,
        config={"task_type": "RETRIEVAL_QUERY"}
    )
    return response.embeddings[0].values

def query_rag(user_query: str, top_k: int = 6) -> dict:
    query_emb = get_query_embedding(user_query)
    results = collection.query(
        query_embeddings=[query_emb],
        n_results=top_k
    )

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    if not documents:
        return {
            "answer": "Não encontrei essa informação na documentação interna disponível.",
            "sources": []
        }

    context = ""
    sources = []
    for doc, meta in zip(documents, metadatas):
        source_name = f"{meta['source']} ({meta['category']})"
        sources.append(source_name)
        context += f"\n--- Documento: {source_name} ---\n{doc}\n"

    prompt = f"""Você é o Assistente Virtual Corporativo interno da empresa.
Responda à dúvida do colaborador sintetizando e correlacionando as informações disponíveis no CONTEXTO abaixo.
Quando a pergunta relacionar mais de um tema ou documento (ex.: estratégia, capacitação, código de conduta, stack técnica), mostre claramente como as informações se complementam.
Se a informação estiver completamente ausente ou não tiver qualquer base ou menção nos documentos, declare: 'Não encontrei essa informação na documentação interna disponível.'
Sempre cite ao final os nomes dos documentos utilizados como referência.

CONTEXTO:
{context}

PERGUNTA DO COLABORADOR:
{user_query}
"""

    candidate_models = [
        "gemini-3.1-flash-lite",
        "gemini-3.5-flash-lite",
        "gemini-3.8-flash",
        "gemini-3.5-flash",
        "gemini-flash-latest"
    ]
    response_text = ""
    last_err = None

    for model_name in candidate_models:
        try:
            response = genai_client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            response_text = response.text
            break
        except Exception as e:
            last_err = e
            continue

    if not response_text and last_err:
        raise last_err

    return {
        "answer": response_text,
        "sources": list(set(sources))
    }
