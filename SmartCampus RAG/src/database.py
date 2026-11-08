import mysql.connector
from mysql.connector import Error
from pathlib import Path
from src.config import (
    MYSQL_HOST,
    MYSQL_PORT,
    MYSQL_USER,
    MYSQL_PASSWORD,
    MYSQL_DATABASE,
    BASE_DIR
)

def get_connection(include_db=True):
    """Cria e retorna uma conexão com o MySQL."""
    kwargs = {
        "host": MYSQL_HOST,
        "port": MYSQL_PORT,
        "user": MYSQL_USER,
        "password": MYSQL_PASSWORD,
        "use_pure": True,
    }
    if include_db:
        kwargs["database"] = MYSQL_DATABASE
    return mysql.connector.connect(**kwargs)

def init_db():
    """Executa os scripts de criação de tabelas, procedures e triggers."""
    conn = None
    try:
        # Primeiro, conecta sem banco para garantir que o banco smartcampus_rag exista
        conn = get_connection(include_db=False)
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {MYSQL_DATABASE} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        conn.commit()
        cursor.close()
        conn.close()

        # Conecta no banco do projeto
        conn = get_connection(include_db=True)
        cursor = conn.cursor()

        # 1. Executa Schema (Tabelas)
        schema_path = BASE_DIR / "sql" / "01_schema.sql"
        if schema_path.exists():
            with open(schema_path, "r", encoding="utf-8") as f:
                schema_sql = f.read()
            for stmt in schema_sql.split(";"):
                stmt = stmt.strip()
                if stmt:
                    cursor.execute(stmt)

        # 2. Executa Procedures
        cursor.execute("DROP PROCEDURE IF EXISTS sp_registrar_pergunta;")
        cursor.execute("""
            CREATE PROCEDURE sp_registrar_pergunta(
                IN p_pergunta TEXT,
                IN p_resposta TEXT,
                IN p_documento_referencia VARCHAR(255),
                IN p_tempo_resposta DECIMAL(6,2),
                OUT p_novo_id INT
            )
            BEGIN
                INSERT INTO historico_perguntas (
                    pergunta, 
                    resposta, 
                    documento_referencia, 
                    tempo_resposta_segundos
                ) VALUES (
                    p_pergunta, 
                    p_resposta, 
                    p_documento_referencia, 
                    p_tempo_resposta
                );
                SET p_novo_id = LAST_INSERT_ID();
            END
        """)

        cursor.execute("DROP PROCEDURE IF EXISTS sp_registrar_documento;")
        cursor.execute("""
            CREATE PROCEDURE sp_registrar_documento(
                IN p_nome_arquivo VARCHAR(255),
                IN p_total_chunks INT,
                OUT p_doc_id INT
            )
            BEGIN
                INSERT INTO documentos (nome_arquivo, total_chunks, status)
                VALUES (p_nome_arquivo, p_total_chunks, 'INDEXADO');
                SET p_doc_id = LAST_INSERT_ID();
            END
        """)

        cursor.execute("DROP PROCEDURE IF EXISTS sp_obter_resumo_estatisticas;")
        cursor.execute("""
            CREATE PROCEDURE sp_obter_resumo_estatisticas()
            BEGIN
                SELECT 
                    e.total_perguntas,
                    e.ultima_interacao,
                    e.tempo_medio_resposta,
                    (SELECT COUNT(*) FROM documentos) AS total_documentos_indexados
                FROM estatisticas_uso e
                WHERE e.id = 1;
            END
        """)

        # 3. Executa Triggers
        cursor.execute("DROP TRIGGER IF EXISTS trg_apos_inserir_pergunta;")
        cursor.execute("""
            CREATE TRIGGER trg_apos_inserir_pergunta
            AFTER INSERT ON historico_perguntas
            FOR EACH ROW
            BEGIN
                UPDATE estatisticas_uso
                SET 
                    total_perguntas = total_perguntas + 1,
                    ultima_interacao = NEW.data_hora,
                    tempo_medio_resposta = (
                        SELECT IFNULL(AVG(tempo_resposta_segundos), 0.00)
                        FROM historico_perguntas
                        WHERE tempo_resposta_segundos IS NOT NULL
                    )
                WHERE id = 1;

                INSERT INTO auditoria_consultas (
                    pergunta_id, 
                    acao, 
                    detalhes, 
                    data_registro
                ) VALUES (
                    NEW.id,
                    'CONSULTA_RAG_REGISTRADA',
                    CONCAT('Doc Ref: ', IFNULL(NEW.documento_referencia, 'Nenhum'), ' | Tempo: ', IFNULL(NEW.tempo_resposta_segundos, 0), 's'),
                    NOW()
                );
            END
        """)

        cursor.execute("DROP TRIGGER IF EXISTS trg_apos_deletar_pergunta;")
        cursor.execute("""
            CREATE TRIGGER trg_apos_deletar_pergunta
            AFTER DELETE ON historico_perguntas
            FOR EACH ROW
            BEGIN
                UPDATE estatisticas_uso
                SET 
                    total_perguntas = (SELECT COUNT(*) FROM historico_perguntas),
                    tempo_medio_resposta = (
                        SELECT IFNULL(AVG(tempo_resposta_segundos), 0.00)
                        FROM historico_perguntas
                        WHERE tempo_resposta_segundos IS NOT NULL
                    )
                WHERE id = 1;
            END
        """)

        conn.commit()
        cursor.close()
        return True, "Banco de dados inicializado com sucesso (Tabelas, Procedures e Triggers criadas)."
    except Error as e:
        return False, f"Erro ao inicializar banco: {e}"
    finally:
        if conn and conn.is_connected():
            conn.close()

def registrar_pergunta_procedure(pergunta: str, resposta: str, doc_ref: str = None, tempo_resposta: float = 0.0):
    """Invoca a Stored Procedure sp_registrar_pergunta."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        # sp_registrar_pergunta(pergunta, resposta, documento, tempo, OUT novo_id)
        args = [pergunta, resposta, doc_ref, tempo_resposta, 0]
        result_args = cursor.callproc("sp_registrar_pergunta", args)
        conn.commit()
        novo_id = result_args[4]
        cursor.close()
        return novo_id
    finally:
        if conn.is_connected():
            conn.close()

def registrar_documento_procedure(nome_arquivo: str, total_chunks: int):
    """Invoca a Stored Procedure sp_registrar_documento."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        args = [nome_arquivo, total_chunks, 0]
        result_args = cursor.callproc("sp_registrar_documento", args)
        conn.commit()
        doc_id = result_args[2]
        cursor.close()
        return doc_id
    finally:
        if conn.is_connected():
            conn.close()

def obter_estatisticas_procedure():
    """Invoca a Stored Procedure sp_obter_resumo_estatisticas."""
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.callproc("sp_obter_resumo_estatisticas")
        resumo = None
        for result in cursor.stored_results():
            resumo = result.fetchone()
        cursor.close()
        return resumo or {
            "total_perguntas": 0,
            "ultima_interacao": None,
            "tempo_medio_resposta": 0.0,
            "total_documentos_indexados": 0
        }
    finally:
        if conn.is_connected():
            conn.close()

def listar_historico(limite: int = 50):
    """Retorna os últimos registros de perguntas e respostas."""
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, pergunta, resposta, documento_referencia, tempo_resposta_segundos, data_hora "
            "FROM historico_perguntas ORDER BY data_hora DESC LIMIT %s",
            (limite,)
        )
        registros = cursor.fetchall()
        cursor.close()
        return registros
    finally:
        if conn.is_connected():
            conn.close()

def listar_auditoria(limite: int = 50):
    """Retorna os registros gerados pela Trigger na tabela de auditoria."""
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, pergunta_id, acao, detalhes, data_registro "
            "FROM auditoria_consultas ORDER BY data_registro DESC LIMIT %s",
            (limite,)
        )
        registros = cursor.fetchall()
        cursor.close()
        return registros
    finally:
        if conn.is_connected():
            conn.close()

def listar_documentos():
    """Retorna os documentos indexados no sistema."""
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, nome_arquivo, total_chunks, data_upload, status FROM documentos ORDER BY data_upload DESC")
        registros = cursor.fetchall()
        cursor.close()
        return registros
    finally:
        if conn.is_connected():
            conn.close()
