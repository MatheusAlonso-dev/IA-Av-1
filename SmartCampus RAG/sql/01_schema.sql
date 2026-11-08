-- Criação do Banco de Dados
CREATE DATABASE IF NOT EXISTS smartcampus_rag
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE smartcampus_rag;

-- Tabela de Documentos Indexados
CREATE TABLE IF NOT EXISTS documentos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome_arquivo VARCHAR(255) NOT NULL,
    total_chunks INT DEFAULT 0,
    data_upload TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'INDEXADO'
) ENGINE=InnoDB;

-- Tabela de Histórico de Perguntas e Respostas
CREATE TABLE IF NOT EXISTS historico_perguntas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pergunta TEXT NOT NULL,
    resposta TEXT NOT NULL,
    documento_referencia VARCHAR(255) NULL,
    tempo_resposta_segundos DECIMAL(6,2) NULL,
    data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Tabela de Estatísticas Globais de Uso
CREATE TABLE IF NOT EXISTS estatisticas_uso (
    id INT PRIMARY KEY,
    total_perguntas INT DEFAULT 0,
    ultima_interacao TIMESTAMP NULL,
    tempo_medio_resposta DECIMAL(6,2) DEFAULT 0.00
) ENGINE=InnoDB;

-- Tabela de Auditoria de Consultas
CREATE TABLE IF NOT EXISTS auditoria_consultas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pergunta_id INT NOT NULL,
    acao VARCHAR(50) NOT NULL,
    detalhes TEXT NULL,
    data_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_auditoria_pergunta FOREIGN KEY (pergunta_id) 
        REFERENCES historico_perguntas(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Inicialização do registro único de estatísticas
INSERT INTO estatisticas_uso (id, total_perguntas, ultima_interacao, tempo_medio_resposta)
SELECT 1, 0, NULL, 0.00
WHERE NOT EXISTS (SELECT 1 FROM estatisticas_uso WHERE id = 1);
