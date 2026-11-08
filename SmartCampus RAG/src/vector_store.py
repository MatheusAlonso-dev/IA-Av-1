import chromadb
from pathlib import Path
from typing import List, Dict, Any
from src.config import CHROMA_PERSIST_DIRECTORY, CHROMA_COLLECTION_NAME
from src.database import registrar_documento_procedure

_client = None
_collection = None

def get_chroma_client():
    """Retorna a instância persistente do cliente ChromaDB."""
    global _client
    if _client is None:
        Path(CHROMA_PERSIST_DIRECTORY).mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIRECTORY)
    return _client

def get_collection():
    """Obtém ou cria a coleção para documentos acadêmicos."""
    global _collection
    if _collection is None:
        client = get_chroma_client()
        # ChromaDB utiliza internamente o all-MiniLM-L6-v2 em ONNX por padrão
        _collection = client.get_or_create_collection(
            name=CHROMA_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )
    return _collection

def indexar_chunks(chunks: List[Dict[str, Any]]) -> int:
    """
    Adiciona os chunks extraídos ao ChromaDB e registra os documentos no MySQL
    utilizando a Stored Procedure sp_registrar_documento.
    """
    if not chunks:
        return 0

    collection = get_collection()
    
    ids = []
    documents = []
    metadatas = []
    
    docs_chunks_count = {}

    for item in chunks:
        doc_id = item["metadados"]["chunk_id"]
        conteudo = item["conteudo"]
        fonte = item["metadados"]["fonte"]

        ids.append(doc_id)
        documents.append(conteudo)
        metadatas.append(item["metadados"])

        docs_chunks_count[fonte] = docs_chunks_count.get(fonte, 0) + 1

    # Insere ou atualiza no ChromaDB
    collection.upsert(
        ids=ids,
        documents=documents,
        metadatas=metadatas
    )

    # Registra cada documento no MySQL usando Stored Procedure
    for nome_arquivo, total in docs_chunks_count.items():
        try:
            registrar_documento_procedure(nome_arquivo, total)
        except Exception as e:
            print(f"[MySQL Warning] Não foi possível registrar documento na Stored Procedure: {e}")

    return len(ids)

def buscar_contexto(query: str, n_results: int = 4) -> List[Dict[str, Any]]:
    """
    Busca semântica no ChromaDB pelos trechos mais relevantes para a pergunta.
    """
    collection = get_collection()
    total_docs = collection.count()
    if total_docs == 0:
        return []

    top_k = min(n_results, total_docs)
    results = collection.query(
        query_texts=[query],
        n_results=top_k,
        include=["documents", "metadatas", "distances"]
    )

    resultados_formatados = []
    if results and "documents" in results and results["documents"]:
        docs = results["documents"][0]
        metas = results["metadatas"][0] if "metadatas" in results else [{}] * len(docs)
        distancias = results["distances"][0] if "distances" in results else [0.0] * len(docs)

        for doc, meta, dist in zip(docs, metas, distancias):
            resultados_formatados.append({
                "conteudo": doc,
                "fonte": meta.get("fonte", "Desconhecido"),
                "pagina": meta.get("pagina", 1),
                "distancia": dist
            })

    return resultados_formatados

def contar_documentos_vetoriais() -> int:
    """Retorna o número total de chunks indexados no ChromaDB."""
    collection = get_collection()
    return collection.count()
