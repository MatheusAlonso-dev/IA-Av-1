import time
from typing import Dict, Any, List
from google import genai
from google.genai import errors
from src.config import GEMINI_API_KEY, GEMINI_MODEL
from src.vector_store import buscar_contexto, contar_documentos_vetoriais
from src.database import registrar_pergunta_procedure

def get_gemini_client():
    """Retorna o cliente autenticado da API Gemini."""
    if not GEMINI_API_KEY:
        return None
    return genai.Client(api_key=GEMINI_API_KEY)

def formatar_prompt(pergunta: str, trechos: List[Dict[str, Any]]) -> str:
    """Monta o prompt para o modelo com o contexto recuperado do ChromaDB."""
    contexto_formatado = ""
    for i, item in enumerate(trechos, start=1):
        contexto_formatado += (
            f"\n--- Trecho {i} [Documento: {item['fonte']} | Página: {item['pagina']}] ---\n"
            f"{item['conteudo']}\n"
        )

    prompt = f"""Você é o assistente virtual acadêmico oficial do SmartCampus RAG.
Sua missão é responder perguntas de alunos e professores utilizando ESTRITAMENTE o contexto acadêmico abaixo.

DIRETRIZES:
1. Responda com tom acadêmico, claro, objetivo e em português.
2. Cite sempre o documento de origem e a página de onde a informação foi extraída.
3. Se a informação não estiver presente no contexto fornecido, informe claramente: "Não encontrei essa informação nos documentos acadêmicos indexados." Não invente dados.

CONTEXTO ACADÊMICO RECUPERADO:
{contexto_formatado}

PERGUNTA DO USUÁRIO:
{pergunta}

RESPOSTA:"""
    return prompt

def responder_pergunta(pergunta: str, n_trechos: int = 4) -> Dict[str, Any]:
    """
    Executa o fluxo completo do RAG:
    1. Recupera chunks mais relevantes no ChromaDB.
    2. Envia para o Gemini sintetizar a resposta.
    3. Persiste a pergunta, resposta e métricas no MySQL via Stored Procedure (disparando a Trigger).
    """
    start_time = time.time()
    
    total_chunks = contar_documentos_vetoriais()
    if total_chunks == 0:
        return {
            "resposta": "Nenhum documento acadêmico foi indexado ainda. Por favor, adicione arquivos PDF ou TXT na pasta de dados ou pela interface.",
            "fontes": [],
            "tempo_resposta": 0.0,
            "id_registro": None
        }

    # 1. Busca semântica no ChromaDB
    trechos = buscar_contexto(pergunta, n_results=n_trechos)
    if not trechos:
        return {
            "resposta": "Não foram encontrados trechos relevantes nos documentos para a sua pergunta.",
            "fontes": [],
            "tempo_resposta": 0.0,
            "id_registro": None
        }

    # 2. Chama a API do Gemini
    client = get_gemini_client()
    if not client:
        return {
            "resposta": "Erro: GEMINI_API_KEY não configurada no arquivo .env. Por favor, adicione sua chave de API para habilitar a geração de respostas.",
            "fontes": trechos,
            "tempo_resposta": 0.0,
            "id_registro": None
        }

    prompt = formatar_prompt(pergunta, trechos)

    texto_resposta = ""
    # Modelos prioritários suportados pela API Gemini
    modelos_candidatos = [GEMINI_MODEL, "gemini-3.1-flash-lite", "gemini-3.8-flash"]
    # Remove duplicatas preservando a ordem
    modelos = list(dict.fromkeys(modelos_candidatos))

    ultimo_erro = None
    for modelo in modelos:
        try:
            response = client.models.generate_content(
                model=modelo,
                contents=prompt
            )
            if response and response.text:
                texto_resposta = response.text
                break
        except Exception as e:
            ultimo_erro = e
            continue

    if not texto_resposta:
        texto_resposta = f"Erro na comunicação com a API Gemini: {str(ultimo_erro)}"

    tempo_resposta = round(time.time() - start_time, 2)

    # Identifica documentos citados
    fontes_unicas = list({item["fonte"] for item in trechos})
    doc_referencia = ", ".join(fontes_unicas) if fontes_unicas else "N/A"

    # 3. Persistência no Banco Relacional (MySQL) via Stored Procedure
    novo_id = None
    try:
        novo_id = registrar_pergunta_procedure(
            pergunta=pergunta,
            resposta=texto_resposta,
            doc_ref=doc_referencia,
            tempo_resposta=tempo_resposta
        )
    except Exception as e:
        print(f"[MySQL Warning] Erro ao executar Stored Procedure sp_registrar_pergunta: {e}")

    return {
        "resposta": texto_resposta,
        "fontes": trechos,
        "tempo_resposta": tempo_resposta,
        "id_registro": novo_id
    }
