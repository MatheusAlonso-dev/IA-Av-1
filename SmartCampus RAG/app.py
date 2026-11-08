import streamlit as st
import time
from pathlib import Path
from src.config import (
    GEMINI_API_KEY, 
    MYSQL_DATABASE, 
    MYSQL_HOST, 
    MYSQL_PORT, 
    MYSQL_USER,
    DATA_DIR
)
from src.database import (
    init_db,
    obter_estatisticas_procedure,
    listar_historico,
    listar_auditoria,
    listar_documentos,
    get_connection
)
from src.document_loader import processar_arquivo, carregar_diretorio
from src.vector_store import (
    indexar_chunks, 
    contar_documentos_vetoriais, 
    get_chroma_client, 
    CHROMA_COLLECTION_NAME
)
from src.rag_engine import responder_pergunta

# Configuração da Página
st.set_page_config(
    page_title="SmartCampus RAG - Assistente Acadêmico",
    page_icon="🎓",
    layout="wide"
)

# Estilo visual moderno
st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 15px;
        border-left: 5px solid #1E88E5;
        margin-bottom: 10px;
    }
    .source-box {
        background-color: #f1f3f4;
        border-radius: 6px;
        padding: 10px;
        margin-top: 8px;
        font-size: 0.9em;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- BARRA LATERAL (CONFIGURAÇÕES & CONTROLE) -----------------
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/graduation-cap.png", width=64)
    st.title("SmartCampus RAG")
    st.caption("Sistema de Inteligência Acadêmica com ChromaDB e MySQL")
    st.divider()

    # Status do Banco Relacional
    st.subheader("🐘 Banco Relacional (MySQL)")
    db_conectado = False
    try:
        conn = get_connection(include_db=False)
        if conn.is_connected():
            db_conectado = True
            conn.close()
            st.success(f"Conectado ao MySQL ({MYSQL_HOST}:{MYSQL_PORT})")
    except Exception as e:
        st.error(f"MySQL desconectado: {e}")

    if st.button("⚡ Inicializar DB (Tabelas, Procedures e Triggers)"):
        with st.spinner("Executando scripts DDL e Stored Procedures..."):
            sucesso, msg = init_db()
            if sucesso:
                st.success(msg)
            else:
                st.error(msg)

    st.divider()

    # Status do ChromaDB
    st.subheader("🔍 ChromaDB (Vetorial)")
    try:
        total_chunks = contar_documentos_vetoriais()
        st.info(f"Chunks indexados: **{total_chunks}**")
    except Exception as e:
        st.warning(f"ChromaDB aguardando inicialização: {e}")
        total_chunks = 0

    st.divider()

    # Upload de Documentos Acadêmicos
    st.subheader("📄 Adicionar Documentos")
    uploaded_files = st.file_uploader(
        "Envie arquivos acadêmicos (PDF ou TXT)", 
        type=["pdf", "txt", "md"], 
        accept_multiple_files=True
    )
    
    if uploaded_files and st.button("📥 Indexar Arquivos"):
        with st.spinner("Processando e gerando embeddings..."):
            total_adicionados = 0
            Path(DATA_DIR).mkdir(parents=True, exist_ok=True)
            for uploaded_file in uploaded_files:
                caminho_salvo = Path(DATA_DIR) / uploaded_file.name
                with open(caminho_salvo, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                chunks = processar_arquivo(caminho_salvo)
                qtd = indexar_chunks(chunks)
                total_adicionados += qtd
            
            st.success(f"{len(uploaded_files)} arquivo(s) indexado(s)! Total de {total_adicionados} novos chunks.")
            time.sleep(1)
            st.rerun()

    # Botão para indexar pasta data/
    if st.button("🔄 Sincronizar pasta data/"):
        with st.spinner("Lendo pasta data/..."):
            chunks = carregar_diretorio(DATA_DIR)
            qtd = indexar_chunks(chunks)
            st.success(f"{qtd} chunks sincronizados da pasta data/!")
            time.sleep(1)
            st.rerun()

    st.divider()
    # Status Gemini API Key
    if GEMINI_API_KEY:
        st.caption("🔑 Gemini API Key: **Configurada**")
    else:
        st.warning("⚠️ GEMINI_API_KEY não encontrada no arquivo .env!")


# ----------------- TELA PRINCIPAL (ABAS) -----------------
tab_chat, tab_metricas, tab_historico, tab_docs = st.tabs([
    "💬 Chat RAG", 
    "📊 Métricas & Triggers", 
    "📜 Histórico & Auditoria", 
    "📁 Documentos Indexados"
])

# ----------------- ABA 1: CHAT RAG -----------------
with tab_chat:
    st.header("Assistente Virtual Acadêmico")
    st.markdown("Faça perguntas sobre os regulamentos, ementas, datas e conteúdos acadêmicos indexados no sistema.")

    # Inicializa o histórico na sessão
    if "mensagens" not in st.session_state:
        st.session_state.mensagens = []

    # Exibe as mensagens anteriores
    for msg in st.session_state.mensagens:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "fontes" in msg and msg["fontes"]:
                with st.expander("📚 Fontes consultadas no ChromaDB"):
                    for item in msg["fontes"]:
                        st.markdown(f"- **{item['fonte']}** (Página {item['pagina']}) - *Distância: {item['distancia']:.4f}*")
                        st.caption(f"> \"{item['conteudo'][:200]}...\"")
            if "tempo" in msg:
                st.caption(f"⏱️ Tempo de resposta: {msg['tempo']}s | Registro DB: #{msg.get('id_registro', 'N/A')}")

    # Entrada de texto do usuário
    if prompt := st.chat_input("Digite sua dúvida acadêmica..."):
        # Adiciona e exibe pergunta do usuário
        st.session_state.mensagens.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Resposta do assistente
        with st.chat_message("assistant"):
            with st.spinner("Pesquisando documentos e gerando resposta..."):
                resultado = responder_pergunta(prompt)
                
                st.markdown(resultado["resposta"])
                
                if resultado["fontes"]:
                    with st.expander("📚 Fontes consultadas no ChromaDB"):
                        for item in resultado["fontes"]:
                            st.markdown(f"- **{item['fonte']}** (Página {item['pagina']}) - *Distância: {item['distancia']:.4f}*")
                            st.caption(f"> \"{item['conteudo'][:200]}...\"")
                            
                st.caption(f"⏱️ Tempo de resposta: {resultado['tempo_resposta']}s | 💾 Stored Procedure ID: #{resultado['id_registro']}")

                # Salva mensagem na sessão
                st.session_state.mensagens.append({
                    "role": "assistant",
                    "content": resultado["resposta"],
                    "fontes": resultado["fontes"],
                    "tempo": resultado["tempo_resposta"],
                    "id_registro": resultado["id_registro"]
                })


# ----------------- ABA 2: MÉTRICAS & TRIGGERS -----------------
with tab_metricas:
    st.header("📊 Painel de Métricas (Consolidação via Triggers)")
    st.markdown("""
    As estatísticas abaixo são geradas e atualizadas em **tempo real** no MySQL 
    através da Stored Procedure `sp_obter_resumo_estatisticas` e alimentadas pela Trigger `trg_apos_inserir_pergunta`.
    """)

    try:
        stats = obter_estatisticas_procedure()
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total de Perguntas", stats.get("total_perguntas", 0))
        with col2:
            tempo_med = stats.get("tempo_medio_resposta") or 0.0
            st.metric("Tempo Médio de Resposta", f"{float(tempo_med):.2f}s")
        with col3:
            st.metric("Documentos Cadastrados", stats.get("total_documentos_indexados", 0))
        with col4:
            ultima = stats.get("ultima_interacao")
            st.metric("Última Consulta", str(ultima)[:19] if ultima else "Nenhuma")

        st.divider()
        st.subheader("💡 Como a Stored Procedure e a Trigger operam:")
        st.markdown("""
        1. **Stored Procedure (`sp_registrar_pergunta`)**: Ao finalizar cada resposta do Gemini, o backend chama esta procedure para persistir atômica e seguramente os dados da interação.
        2. **Trigger (`trg_apos_inserir_pergunta`)**: Disparada automaticamente pelo MySQL após a inserção em `historico_perguntas`, ela:
           - Incrementa o contador total em `estatisticas_uso`.
           - Recalcula a média global de tempo de resposta.
           - Insere um registro na tabela `auditoria_consultas` para fins de compliance acadêmica.
        """)
    except Exception as e:
        st.error(f"Erro ao carregar estatísticas do banco: {e}")


# ----------------- ABA 3: HISTÓRICO & AUDITORIA -----------------
with tab_historico:
    st.header("📜 Histórico e Tabela de Auditoria")
    
    col_hist, col_audit = st.columns(2)
    
    with col_hist:
        st.subheader("💬 Histórico de Perguntas (`historico_perguntas`)")
        try:
            historico = listar_historico(limite=30)
            if historico:
                for h in historico:
                    with st.expander(f"#{h['id']} - {h['pergunta'][:50]}... ({h['data_hora']})"):
                        st.markdown(f"**Pergunta:** {h['pergunta']}")
                        st.markdown(f"**Resposta:** {h['resposta']}")
                        st.caption(f"Fonte: {h['documento_referencia']} | Duração: {h['tempo_resposta_segundos']}s")
            else:
                st.info("Nenhuma pergunta registrada no histórico ainda.")
        except Exception as e:
            st.error(f"Erro ao buscar histórico: {e}")

    with col_audit:
        st.subheader("🛡️ Tabela de Auditoria Alimentada por Trigger (`auditoria_consultas`)")
        try:
            auditoria = listar_auditoria(limite=30)
            if auditoria:
                st.dataframe(auditoria, use_container_width=True)
            else:
                st.info("Nenhum log de auditoria gerado ainda.")
        except Exception as e:
            st.error(f"Erro ao buscar logs de auditoria: {e}")


# ----------------- ABA 4: DOCUMENTOS INDEXADOS -----------------
with tab_docs:
    st.header("📁 Documentos Cadastrados no Banco Relacional")
    st.markdown("Lista de documentos registrados via Stored Procedure `sp_registrar_documento`:")
    try:
        docs = listar_documentos()
        if docs:
            st.dataframe(docs, use_container_width=True)
        else:
            st.info("Nenhum documento cadastrado na tabela `documentos` ainda.")
    except Exception as e:
        st.error(f"Erro ao buscar lista de documentos: {e}")
