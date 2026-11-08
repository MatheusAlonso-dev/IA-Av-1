USE smartcampus_rag;

DROP TRIGGER IF EXISTS trg_apos_inserir_pergunta;
DROP TRIGGER IF EXISTS trg_apos_deletar_pergunta;

DELIMITER //

-- Trigger disparada automaticamente após inserção de uma pergunta
CREATE TRIGGER trg_apos_inserir_pergunta
AFTER INSERT ON historico_perguntas
FOR EACH ROW
BEGIN
    -- 1. Atualiza a tabela de estatísticas agregadas
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

    -- 2. Insere registro automático na tabela de auditoria
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
END //

-- Trigger para manter estatísticas consistentes se registros forem removidos
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
END //

DELIMITER ;
