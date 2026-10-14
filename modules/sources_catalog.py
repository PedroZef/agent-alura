import os
import mimetypes
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

# Mapeamento oficial de URLs externas e títulos amigáveis
OFFICIAL_SOURCES_METADATA = {
    "tabela_precos_planos_2026.csv": {
        "title": "Tabela de Preços e Planos 2026",
        "web_link": "https://www.alura.com.br/empresas",
        "category": "comercial",
    },
    "Brasscom_Alura.docx": {
        "title": "Parceria Estratégica Alura & Brasscom",
        "web_link": "https://www.alura.com.br/artigos/brasscom",
        "category": "edTech",
    },
    "Demanda-de-Talentos-em-TIC.pdf": {
        "title": "Relatório de Demanda de Talentos em TIC (Brasscom)",
        "web_link": "https://brasscom.org.br/relatorios-brasscom/",
        "category": "edTech",
    },
    "Demanda-de-Talentos-em-TIC.txt": {
        "title": "Demanda de Talentos em TIC (Transcrição Textual)",
        "web_link": "https://brasscom.org.br/relatorios-brasscom/",
        "category": "operacional",
    },
    "analise_brasscom_estrategia.md": {
        "title": "Análise Estratégica Setorial auFOOD & Alura",
        "web_link": "https://www.alura.com.br/empresas/solucoes",
        "category": "financeiro",
    },
    "Relatorio_Brasscom_Demanda_Talentos_TIC_2026.pdf": {
        "title": "Relatório Brasscom Demanda Talentos TIC 2026",
        "web_link": "https://brasscom.org.br/relatorios-brasscom/",
        "category": "financeiro",
    },
    "nda_contrato_sigilo.docx": {
        "title": "Acordo de Confidencialidade e Sigilo (NDA auFOOD)",
        "web_link": "https://legal.aufood.internal/politica-sigilo",
        "category": "legal",
    },
    "onboarding_devs.pptx": {
        "title": "Apresentação de Onboarding & Stack Técnica de TI",
        "web_link": "https://wiki.aufood.internal/engenharia/onboarding",
        "category": "operacional",
    },
    "Codigo-de-Conduta-SERIS.pdf": {
        "title": "Código de Conduta e Integridade Corporativa",
        "web_link": "https://rh.aufood.internal/codigo-conduta",
        "category": "rh",
    },
    "intranet_avisos.html": {
        "title": "Portal Intranet - Comunicados Oficiais auFOOD",
        "web_link": "https://intranet.aufood.internal/avisos",
        "category": "rh",
    },
    "catalogo_apis_integracao.json": {
        "title": "Catálogo de APIs e Microsserviços de Integração",
        "web_link": "https://agent.aufood.internal/api/v1/docs",
        "category": "sistemas",
    },
}

MIME_TYPE_OVERRIDES = {
    ".csv": "text/csv",
    ".md": "text/markdown",
    ".json": "application/json",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".pdf": "application/pdf",
    ".html": "text/html",
    ".txt": "text/plain",
}


def parse_source_string(source_str: str) -> tuple[str, str]:
    """
    Interpreta formatos como 'tabela_precos_planos_2026.csv (comercial)'
    retornando ('tabela_precos_planos_2026.csv', 'comercial').
    """
    clean_str = source_str.strip()
    match = re.match(r"^(.+?)\s*\((.+?)\)$", clean_str)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return clean_str, ""


def find_file_in_data(filename: str, category: str = "") -> str | None:
    """
    Localiza o arquivo físico dentro da pasta data/.
    """
    if category:
        candidate = os.path.join(DATA_DIR, category, filename)
        if os.path.isfile(candidate):
            return candidate

    for root, _, files in os.walk(DATA_DIR):
        if filename in files:
            return os.path.join(root, filename)

    return None


def get_source_metadata(source_str: str) -> dict:
    """
    Retorna dicionário completo com metadados da fonte, caminho local e link oficial.
    """
    filename, parsed_cat = parse_source_string(source_str)
    known = OFFICIAL_SOURCES_METADATA.get(filename, {})

    category = parsed_cat or known.get("category", "geral")
    title = known.get("title", filename)
    web_link = known.get("web_link", "https://www.alura.com.br")

    abs_path = find_file_in_data(filename, category)
    rel_path = (
        os.path.relpath(abs_path, BASE_DIR).replace("\\", "/")
        if abs_path
        else f"data/{category}/{filename}"
    )

    ext = os.path.splitext(filename)[1].lower()
    mime_type = MIME_TYPE_OVERRIDES.get(
        ext, mimetypes.guess_type(filename)[0] or "application/octet-stream"
    )

    return {
        "raw_source": source_str,
        "filename": filename,
        "category": category,
        "title": title,
        "web_link": web_link,
        "relative_path": rel_path,
        "absolute_path": abs_path,
        "exists": abs_path is not None and os.path.isfile(abs_path),
        "mime_type": mime_type,
    }


def format_sources_for_prompt(sources_metadata: list[dict]) -> str:
    """
    Formata lista de fontes com links para enriquecer o contexto passado ao Gemini.
    """
    lines = []
    for meta in sources_metadata:
        title = meta.get("title", meta.get("filename", "Documento"))
        url = meta.get("web_link", "")
        if url:
            lines.append(f"- [{title}]({url}) (Arquivo: `{meta.get('filename')}`)")
        else:
            lines.append(f"- {title} (Arquivo: `{meta.get('filename')}`)")
    return "\n".join(lines)


def read_file_bytes(file_path: str) -> bytes:
    """
    Leitura sob demanda dos bytes do arquivo.
    """
    if not file_path or not os.path.isfile(file_path):
        return b""
    with open(file_path, "rb") as f:
        return f.read()


def get_file_preview_content(file_path: str, max_chars: int = 1500) -> str:
    """
    Retorna uma prévia em texto do conteúdo do arquivo de forma leve e segura para memória.
    """
    if not file_path or not os.path.isfile(file_path):
        return ""

    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext in [".txt", ".md", ".csv", ".json", ".html"]:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(max_chars)
                if len(content) == max_chars:
                    content += "\n... [conteúdo truncado para visualização rápida]"
                return content
        elif ext == ".pdf":
            try:
                from pypdf import PdfReader
                reader = PdfReader(file_path)
                first_page = reader.pages[0].extract_text() or ""
                return f"[Prévia da Página 1 do PDF]\n{first_page[:max_chars]}"
            except Exception:
                return f"Documento PDF ({os.path.basename(file_path)}). Use o botão de download para abrir o arquivo completo."
        elif ext in [".docx", ".pptx", ".xlsx", ".xls"]:
            return f"Arquivo binário de escritório ({ext.upper()}). Use o botão de download para abrir no aplicativo correspondente."
        else:
            return f"Arquivo {ext.upper()}. Use o botão de download para acessá-lo."
    except Exception as e:
        return f"Não foi possível gerar a prévia do arquivo: {e}"
