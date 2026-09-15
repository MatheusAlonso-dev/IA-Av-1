from google import genai
from google.genai import errors

chave = "minhachave"

cliente = genai.Client(api_key=chave)

padrao = '''
{
  "titulo": "",
  "data_prevista": "",
  "genero": "",
  "diretor": "",
  "elenco": [],
  "sinopse": "",
  "expectativa": ""
}
'''

txtInput = f"""
<prompt>
    <instrucao>
        Liste os 5 filmes mais aguardados para lançamento a partir da data de hoje.
    </instrucao>

    <formato>
        A resposta deve seguir exatamente este formato:
        {padrao}
    </formato>

    <regras>
        <regra>Responda exclusivamente com o JSON solicitado.</regra>
        <regra>Não escreva explicações, introduções ou conclusões.</regra>
        <regra>Não utilize Markdown ou blocos de código.</regra>
        <regra>Não escreva nenhum texto antes ou depois do JSON.</regra>
        <regra>Retorne exatamente 5 filmes.</regra>
        <regra>Considere a data de hoje como referência para os lançamentos.</regra>
    </regras>
</prompt>
"""


print("Conectando ao Gemini...")

try:
    resposta = cliente.interactions.create(
        model="gemini-3.6-flash",
        input=txtInput
    )

    print(resposta.output_text)

except errors.ServerError as erro:
    if erro.code == 503:
        print("O Gemini está temporariamente sobrecarregado.")
        print("Tente novamente daqui a pouco.")
    else:
        print("Erro do servidor:", erro)

except errors.APIError as erro:
    print("Erro da API:", erro)