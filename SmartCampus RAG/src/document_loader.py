import os
from pathlib import Path
from typing import List, Dict, Any
from pypdf import PdfReader

def extrair_texto_pdf(caminho_pdf: Path | str) -> List[Dict[str, Any]]:
    """
    Extrai o texto de um arquivo PDF, retornando uma lista de páginas com metadados.
    """
    paginas = []
    caminho = Path(caminho_pdf)
    
    try:
        reader = PdfReader(str(caminho))
        for num_pagina, pagina in enumerate(reader.pages, start=1):
            texto = pagina.extract_text()
            if texto and texto.strip():
                paginas.append({
                    "texto": texto.strip(),
                    "fonte": caminho.name,
                    "pagina": num_pagina
                })
    except Exception as e:
        print(f"Erro ao ler PDF {caminho.name}: {e}")
        
    return paginas

def extrair_texto_txt(caminho_txt: Path | str) -> List[Dict[str, Any]]:
    """Extrai texto de arquivo TXT ou Markdown."""
    caminho = Path(caminho_txt)
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            conteudo = f.read()
        if conteudo.strip():
            return [{
                "texto": conteudo.strip(),
                "fonte": caminho.name,
                "pagina": 1
            }]
    except Exception as e:
        print(f"Erro ao ler TXT {caminho.name}: {e}")
    return []

def dividir_em_chunks(
    paginas: List[Dict[str, Any]], 
    chunk_size: int = 700, 
    chunk_overlap: int = 150
) -> List[Dict[str, Any]]:
    """
    Divide o texto em chunks (pedaços) menores mantendo sobreposição (overlap)
    para preservar a coerência semântica.
    """
    chunks = []
    
    for item in paginas:
        texto = item["texto"]
        fonte = item["fonte"]
        pagina = item["pagina"]
        
        inicio = 0
        comprimento = len(texto)
        chunk_idx = 0
        
        while inicio < comprimento:
            fim = inicio + chunk_size
            trecho = texto[inicio:fim]
            
            # Tenta não cortar palavras no meio se houver espaço próximo ao fim
            if fim < comprimento:
                ultimo_espaco = trecho.rfind(" ")
                if ultimo_espaco != -1 and ultimo_espaco > chunk_size * 0.7:
                    trecho = trecho[:ultimo_espaco]
                    fim = inicio + ultimo_espaco
            
            chunks.append({
                "conteudo": trecho.strip(),
                "metadados": {
                    "fonte": fonte,
                    "pagina": pagina,
                    "chunk_id": f"{fonte}_p{pagina}_c{chunk_idx}"
                }
            })
            
            chunk_idx += 1
            inicio = fim - chunk_overlap if fim < comprimento else comprimento
            
    return chunks

def processar_arquivo(caminho_arquivo: Path | str) -> List[Dict[str, Any]]:
    """Processa um arquivo individual (PDF ou TXT) e retorna seus chunks."""
    caminho = Path(caminho_arquivo)
    ext = caminho.suffix.lower()
    
    if ext == ".pdf":
        paginas = extrair_texto_pdf(caminho)
    elif ext in [".txt", ".md"]:
        paginas = extrair_texto_txt(caminho)
    else:
        return []
        
    return dividir_em_chunks(paginas)

def carregar_diretorio(diretorio: Path | str) -> List[Dict[str, Any]]:
    """Carrega todos os arquivos suportados de um diretório."""
    caminho_dir = Path(diretorio)
    if not caminho_dir.exists():
        caminho_dir.mkdir(parents=True, exist_ok=True)
        return []
        
    todos_chunks = []
    for arquivo in caminho_dir.glob("*.*"):
        if arquivo.suffix.lower() in [".pdf", ".txt", ".md"]:
            chunks = processar_arquivo(arquivo)
            todos_chunks.extend(chunks)
            
    return todos_chunks
