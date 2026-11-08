USE smartcampus_rag;

DROP PROCEDURE IF EXISTS sp_registrar_pergunta;
DROP PROCEDURE IF EXISTS sp_registrar_documento;
DROP PROCEDURE IF EXISTS sp_obter_resumo_estatisticas;

DELIMITER //

-- Procedure para registrar uma interação no RAG
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
END //

-- Procedure para cadastrar ou atualizar documento indexado
CREATE PROCEDURE sp_registrar_documento(
    IN p_nome_arquivo VARCHAR(255),
    IN p_total_chunks INT,
    OUT p_doc_id INT
)
BEGIN
    INSERT INTO documentos (nome_arquivo, total_chunks, status)
    VALUES (p_nome_arquivo, p_total_chunks, 'INDEXADO');
    
    SET p_doc_id = LAST_INSERT_ID();
END //

-- Procedure para retornar relatório consolidado
CREATE PROCEDURE sp_obter_resumo_estatisticas()
BEGIN
    SELECT 
        e.total_perguntas,
        e.ultima_interacao,
        e.tempo_medio_resposta,
        (SELECT COUNT(*) FROM documentos) AS total_documentos_indexados
    FROM estatisticas_uso e
    WHERE e.id = 1;
END //

DELIMITER ;
