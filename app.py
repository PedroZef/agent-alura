import streamlit as st  # pyright: ignore[reportMissingImports]
import json
import os
import sys
from datetime import datetime
import importlib

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODULES_DIR = os.path.join(SCRIPT_DIR, "modules")
for p in [SCRIPT_DIR, MODULES_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    try:
        from modules.rag_engine import (
            query_rag,
        )  # pyright: ignore[reportUnknownVariableType]
    except ModuleNotFoundError:
        from rag_engine import ( # pyright: ignore[reportMissingImports]
            query_rag,
        )  # pyright: ignore[reportUnknownVariableType, reportMissingImports]
except Exception as e:

    def query_rag(_prompt):  # pyright: ignore[reportUnknownParameterType]
        return {
            "answer": f"Não foi possível carregar o módulo 'rag_engine': {e}",
            "sources": [],
        }  # pyright: ignore[reportUnknownVariableType]


FEEDBACK_FILE = os.path.join(SCRIPT_DIR, "feedback_logs.json")


def load_feedbacks():  # pyright: ignore[reportUnknownParameterType]
    if not os.path.exists(FEEDBACK_FILE):
        return []
    try:
        with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_feedback(
    query, answer, feedback_type
):  # pyright: ignore[reportUnknownParameterType]
    feedbacks = load_feedbacks()
    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "pergunta": query,
        "resposta": answer[:150] + "..." if len(answer) > 150 else answer,
        "avaliacao": feedback_type,
    }
    feedbacks.append(entry)
    with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
        json.dump(feedbacks, f, indent=2, ensure_ascii=False)


def clear_feedbacks():  # pyright: ignore[reportUnknownParameterType]
    try:
        with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


st.set_page_config(page_title="🤖 Agente Alura", layout="wide")

# --- SIDEBAR: LOGS E MÉTRICAS ---
st.sidebar.title("📊 Painel de Avaliações")
feedbacks = load_feedbacks()
total_positivos = sum(1 for f in feedbacks if f["avaliacao"] == "Positivo")
total_negativos = sum(1 for f in feedbacks if f["avaliacao"] == "Negativo")

col1, col2 = st.sidebar.columns(2)
col1.metric("👍 Positivos", total_positivos)
col2.metric("👎 Negativos", total_negativos)

# --- CONTROLES DE CONVERSA ---
st.sidebar.markdown("---")
st.sidebar.subheader("💬 Gerenciar Conversa")
if st.sidebar.button(
    "🗑️ Limpar Histórico do Chat",
    help="Apaga todas as mensagens da conversa na sessão atual",
    use_container_width=True,
):
    st.session_state.messages = []
    st.toast("Histórico da conversa limpo com sucesso!", icon="🧹")
    st.rerun()

esconder_historico = st.sidebar.toggle(
    "👁️ Ocultar Mensagens no Navegador",
    value=False,
    help="Oculta temporariamente o histórico de perguntas e respostas da tela",
)

# --- ARQUITETURA DO AGENTE ---
st.sidebar.markdown("---")
with st.sidebar.expander("🗺️ Arquitetura do Agente Alura", expanded=False):
    rag_img_path = os.path.join(SCRIPT_DIR, "docs", "RAG.png")
    if os.path.exists(rag_img_path):
        st.image(
            rag_img_path,
            caption="Fluxo do Agente: Decisão, Geração de Queries, Recuperação e Síntese",
        )
    else:
        st.caption("Imagem não encontrada.")

st.sidebar.markdown("---")
st.sidebar.subheader("Histórico de Feedback")
if feedbacks:
    if st.sidebar.button(
        "🗑️ Limpar Avaliações",
        help="Apaga todos os registros de feedback salvos no arquivo de logs",
        use_container_width=True,
    ):
        clear_feedbacks()
        st.toast("Logs de avaliações limpos com sucesso!", icon="🧹")
        st.rerun()

    for item in reversed(feedbacks[-10:]):  # Últimos 10 feedbacks
        icone = "🟢" if item["avaliacao"] == "Positivo" else "🔴"
        st.sidebar.markdown(f"**{icone} {item['avaliacao']}** - *{item['timestamp']}*")
        st.sidebar.caption(f"Q: {item['pergunta']}")
        st.sidebar.divider()
else:
    st.sidebar.info("Nenhuma avaliação registrada ainda.")

st.sidebar.markdown("---")
st.sidebar.markdown(
    "<div style='text-align: center; color: #1E88E5; font-size: 0.9rem; font-weight: 500; padding: 6px 0;'>"
    "@2026 - Pedro Zeferino da Silva."
    "</div>",
    unsafe_allow_html=True,
)

# --- CHAT PRINCIPAL ---
st.title("🤖 Agente Alura")
st.caption("Base de Conhecimento Corporativa")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Exibe histórico do chat
if esconder_historico:
    if st.session_state.messages:
        st.info(
            "👁️ O histórico de mensagens está oculto na tela. Desmarque a opção **Ocultar Mensagens no Navegador** na barra lateral para exibi-lo novamente."
        )
else:
    for idx, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "workflow" in msg and msg["workflow"]:
                wf = msg["workflow"]
                with st.expander("⚡ Fluxo de Execução do Agente Alura"):
                    st.markdown(
                        f"- **Conhecimento Externo Necessário:** {'Sim' if wf.get('needs_external_knowledge') else 'Não'}"
                    )
                    if wf.get("generated_queries"):
                        st.markdown(
                            f"- **Queries de Busca Geradas:** `{', '.join(wf['generated_queries'])}`"
                        )
                    if wf.get("search_rounds"):
                        st.markdown(f"- **Rodadas de Busca:** `{wf['search_rounds']}`")
                    if wf.get("requires_more_search"):
                        st.markdown(
                            "- **Busca Adicional:** Ativada para complementar contexto faltante."
                        )

            if "sources" in msg and msg["sources"]:
                with st.expander("📚 Fontes consultadas"):
                    for src in msg["sources"]:
                        st.write(f"- {src}")

            # Botões de feedback para mensagens do assistente
            if msg["role"] == "assistant":
                f_col1, f_col2, _ = st.columns([1, 1, 8])
                with f_col1:
                    if st.button("👍", key=f"pos_{idx}"):
                        user_q = (
                            st.session_state.messages[idx - 1]["content"]
                            if idx > 0
                            else "N/A"
                        )
                        save_feedback(user_q, msg["content"], "Positivo")
                        st.toast("Avaliação positiva registrada!", icon="✅")
                        st.rerun()
                with f_col2:
                    if st.button("👎", key=f"neg_{idx}"):
                        user_q = (
                            st.session_state.messages[idx - 1]["content"]
                            if idx > 0
                            else "N/A"
                        )
                        save_feedback(user_q, msg["content"], "Negativo")
                        st.toast("Avaliação negativa registrada!", icon="⚠️")
                        st.rerun()

# Entrada de pergunta
if prompt := st.chat_input("Digite sua dúvida sobre a empresa..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Consultando base de conhecimento..."):
            try:
                result = query_rag(prompt)
            except Exception as e:
                result = {
                    "answer": f"Ocorreu um erro ao consultar o assistente: {e}",
                    "sources": [],
                    "workflow": {},
                }
            st.markdown(result["answer"])
            if result.get("workflow"):
                wf = result["workflow"]
                with st.expander("⚡ Fluxo de Execução do Agente Alura"):
                    st.markdown(
                        f"- **Conhecimento Externo Necessário:** {'Sim' if wf.get('needs_external_knowledge') else 'Não'}"
                    )
                    if wf.get("generated_queries"):
                        st.markdown(
                            f"- **Queries de Busca Geradas:** `{', '.join(wf['generated_queries'])}`"
                        )
                    if wf.get("search_rounds"):
                        st.markdown(f"- **Rodadas de Busca:** `{wf['search_rounds']}`")
                    if wf.get("requires_more_search"):
                        st.markdown(
                            "- **Busca Adicional:** Ativada para complementar contexto faltante."
                        )
            if result.get("sources"):
                with st.expander("📚 Fontes consultadas"):
                    for src in result["sources"]:
                        st.write(f"- {src}")

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": result["answer"],
            "sources": result.get("sources", []),
            "workflow": result.get("workflow", {}),
        }
    )
    st.rerun()

# --- FOOTER ---
if hasattr(st, "bottom"):
    with st.bottom:
        st.markdown(
            "<div style='text-align: center; color: #1E88E5; font-size: 0.95rem; font-weight: 500; padding: 6px 0;'>"
            "@2026 - Pedro Zeferino da Silva."
            "</div>",
            unsafe_allow_html=True,
        )
else:
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #1E88E5; font-size: 0.95rem; font-weight: 500; padding: 6px 0;'>"
        "@2026 - Pedro Zeferino da Silva."
        "</div>",
        unsafe_allow_html=True,
    )
