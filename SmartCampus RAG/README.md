# 🎓 SmartCampus RAG

> Sistema acadêmico inteligente para resposta a dúvidas sobre regulamentos e ementas utilizando **RAG (Retrieval-Augmented Generation)**, **ChromaDB** e integração completa com **MySQL** com **Stored Procedures** e **Triggers**.

---

## 📌 Requisitos Atendidos

- [x] **RAG com Documentos Acadêmicos**: Extração, segmentação em *chunks* e geração de respostas contextualizadas com citação de fontes (arquivo e página).
- [x] **ChromaDB**: Banco vetorial local utilizando *embeddings* com modelo `all-MiniLM-L6-v2` em formato ONNX de alta performance.
- [x] **Integração com Banco Relacional (MySQL)**: Persistência de documentos indexados, histórico de perguntas e auditoria.
- [x] **Stored Procedures**:
  - `sp_registrar_pergunta`: Insere a pergunta, resposta gerada, fonte e tempo de execução.
  - `sp_registrar_documento`: Registra metadados e total de chunks de cada documento.
  - `sp_obter_resumo_estatisticas`: Consolida métricas de uso do sistema.
- [x] **Triggers**:
  - `trg_apos_inserir_pergunta`: Disparada após nova interação para atualizar em tempo real contadores e tempo médio na tabela `estatisticas_uso`, e gerar log automático em `auditoria_consultas`.
  - `trg_apos_deletar_pergunta`: Mantém consistência métrica caso registros sejam apagados.
- [x] **Interface Gráfica (Streamlit)**: Chat conversacional, upload de arquivos, painel de métricas e visualizador de tabelas do banco.

---

## 🏗️ Arquitetura do Sistema

```
[ Usuário ]
     │
     ▼
[ Interface Streamlit (app.py) ]
     │
     ├── 1. Pergunta do Usuário
     ▼
[ ChromaDB (Vector Store) ] ──────────► Recupera os Top-k Chunks Acadêmicos
     │
     ├── 2. Prompt (Contexto + Pergunta)
     ▼
[ Google Gemini API (LLM) ] ──────────► Sintetiza a Resposta com Citação
     │
     ├── 3. Resposta Gerada
     ▼
[ MySQL Database ]
     ├── 1. Executa Stored Procedure: sp_registrar_pergunta(...)
     └── 2. Dispara Trigger: trg_apos_inserir_pergunta
              ├── Atualiza tabela: estatisticas_uso
              └── Grava log em: auditoria_consultas
```

---

## 📂 Estrutura de Diretórios

```text
SmartCampus RAG/
├── data/                          # Documentos acadêmicos (PDFs, TXTs)
│   └── regulamento_academico_exemplo.txt
├── chromadb_data/                 # Armazenamento vetorial persistente
├── sql/                           # Scripts DDL para o MySQL
│   ├── 01_schema.sql              # Criação das tabelas
│   ├── 02_procedures.sql          # Stored Procedures
│   └── 03_triggers.sql            # Triggers de auditoria e métricas
├── src/
│   ├── config.py                  # Leitura de variáveis de ambiente (.env)
│   ├── database.py                # Conexão MySQL e chamadas de Procedures
│   ├── document_loader.py         # Leitura de PDFs/TXTs e chunking
│   ├── vector_store.py            # ChromaDB e busca por similaridade
│   └── rag_engine.py              # Orquestração do RAG e chamada ao Gemini
├── app.py                         # Interface Web Interativa (Streamlit)
├── requirements.txt               # Dependências Python
├── .env.example                   # Modelo de configuração
└── README.md                      # Documentação completa
```

---

## 🚀 Como Executar o Projeto

### 1. Pré-requisitos
- Python 3.10+ instalado.
- Servidor MySQL 8.0+ rodando localmente (porta 3306).
- Chave de API gratuita do Google Gemini ([obter no Google AI Studio](https://aistudio.google.com/)).

### 2. Configurar o arquivo `.env`
Abra o arquivo `.env` na raiz do projeto e preencha sua senha do MySQL e a chave do Gemini:
```env
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=sua_senha_do_mysql
MYSQL_DATABASE=smartcampus_rag

GEMINI_API_KEY=sua_chave_gemini_aqui
```

### 3. Iniciar a Aplicação
Ative o ambiente virtual e execute o Streamlit:
```powershell
.\.venv\Scripts\streamlit run app.py
```

### 4. Primeiro Uso na Interface
1. Na barra lateral da interface, clique em **"⚡ Inicializar DB (Tabelas, Procedures e Triggers)"** para criar a estrutura no MySQL.
2. Clique em **"🔄 Sincronizar pasta data/"** ou envie seus próprios PDFs através do campo de upload.
3. Acesse a aba **💬 Chat RAG** e faça suas perguntas acadêmicas!
4. Acesse as abas **📊 Métricas & Triggers** e **📜 Histórico & Auditoria** para observar os dados sendo persistidos e os Triggers sendo disparados em tempo real.
