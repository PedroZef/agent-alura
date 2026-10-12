import os
import json
import pandas as pd
from bs4 import BeautifulSoup
from pypdf import PdfReader
from docx import Document
from pptx import Presentation
from google import genai
import chromadb
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROMA_DATA_PATH = os.path.join(BASE_DIR, "chroma_db")
DATA_DIR = os.path.join(BASE_DIR, "data")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("Chave de API não encontrada. Defina GEMINI_API_KEY ou GOOGLE_API_KEY no arquivo .env.")

genai_client = genai.Client(api_key=GEMINI_API_KEY)

def extract_text_from_file(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    text = ""
    try:
        if ext == ".pdf":
            reader = PdfReader(file_path)
            text = "\n".join([page.extract_text() or "" for page in reader.pages])
        elif ext == ".docx":
            try:
                doc = Document(file_path)
                lines = [p.text for p in doc.paragraphs if p.text]
                for table in doc.tables:
                    for row in table.rows:
                        row_text = " | ".join([cell.text.strip() for cell in row.cells if cell.text.strip()])
                        if row_text:
                            lines.append(row_text)
                text = "\n".join(lines)
            except Exception:
                import docx2txt
                text = docx2txt.process(file_path) or ""
        elif ext in [".xlsx", ".xls"]:
            excel = pd.read_excel(file_path, sheet_name=None)
            for sheet, df in excel.items():
                text += f"\n--- Aba: {sheet} ---\n" + df.to_string(index=False)
        elif ext == ".csv":
            df = pd.read_csv(file_path)
            text = df.to_string(index=False)
        elif ext == ".pptx":
            prs = Presentation(file_path)
            for slide in prs.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text"):
                        text += shape.text + "\n"
        elif ext == ".json":
            with open(file_path, "r", encoding="utf-8") as f:
                text = json.dumps(json.load(f), indent=2, ensure_ascii=False)
        elif ext == ".html":
            with open(file_path, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f.read(), "html.parser")
                text = soup.get_text(separator="\n")
        elif ext in [".md", ".txt"]:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
    except Exception as e:
        print(f"Erro ao ler {file_path}: {e}")
    return text.strip()

def chunk_text(text: str, chunk_size: int = 700, overlap: int = 100) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks

def generate_embedding(text: str) -> list[float]:
    response = genai_client.models.embed_content(
        model="gemini-embedding-001",
        contents=text,
        config={"task_type": "RETRIEVAL_DOCUMENT"}
    )
    return response.embeddings[0].values

def run_ingestion():
    client = chromadb.PersistentClient(path=CHROMA_DATA_PATH)
    collection = client.get_or_create_collection(name="documentos_empresa")

    print(f"Iniciando ingestão de documentos a partir de: {DATA_DIR}")
    print(f"Banco ChromaDB: {CHROMA_DATA_PATH}")
    doc_id = 0

    for root, _, files in os.walk(DATA_DIR):
        for file in files:
            file_path = os.path.join(root, file)
            category = os.path.basename(root)
            raw_text = extract_text_from_file(file_path)

            if not raw_text:
                continue

            chunks = chunk_text(raw_text)
            for idx, chunk in enumerate(chunks):
                emb = generate_embedding(chunk)
                collection.upsert(
                    ids=[f"doc_{category}_{file}_{idx}"],
                    embeddings=[emb],
                    documents=[chunk],
                    metadatas=[{
                        "source": file,
                        "category": category,
                        "chunk_index": idx
                    }]
                )
                doc_id += 1
                print(f"Indexado: {file} (bloco {idx})")

    print(f"Ingestão concluída. Total de blocos indexados: {doc_id}")

if __name__ == "__main__":
    run_ingestion()