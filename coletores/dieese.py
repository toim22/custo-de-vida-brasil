"""DIEESE: salário mínimo nominal e necessário (mensal) e Pesquisa Nacional da Cesta Básica (mensal)."""
import io
import re

import pandas as pd

from comum import INICIO, baixar, norm, salvar_json, ler_json

URL_SALARIO = "https://www.dieese.org.br/analisecestabasica/salarioMinimo.html"
MESES = {m: i + 1 for i, m in enumerate(
    ["janeiro", "fevereiro", "marco", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"])}


def reais(txt):
    s = str(txt)
    m = re.search(r"([\d\.]+,\d{2})", s)
    if not m:
        return None
    return float(m.group(1).replace(".", "").replace(",", "."))


def coletar_salario():
    html = baixar(URL_SALARIO).text
    tabelas = pd.read_html(io.StringIO(html), decimal=",", thousands=".")
    alvo = None
    for t in tabelas:
        cab = " ".join(norm(c) for c in t.columns.astype(str))
        if "necessario" in cab or (t.shape[1] >= 3 and t.astype(str).apply(lambda c: c.str.contains("necess", case=False)).any().any()):
            alvo = t
            break
    if alvo is None:
        raise RuntimeError("tabela do salário mínimo não encontrada")
    serie = {}
    ano = None
    for _, linha in alvo.iterrows():
        cel = [str(x) for x in linha.tolist()]
        periodo = norm(cel[0])
        if re.fullmatch(r"\d{4}", periodo):
            ano = int(periodo)
            continue
        mes = MESES.get(periodo)
        if not (ano and mes):
            continue
        nominal, necessario = reais(cel[1]), reais(cel[2])
        chave = f"{ano}-{mes:02d}"
        if chave >= INICIO[:7] and nominal:
            serie[chave] = [nominal, necessario]
    if not serie:
        raise RuntimeError("nenhuma linha do salário mínimo lida")
    pontos = [[k, v[0], v[1]] for k, v in sorted(serie.items())]
    salvar_json("salario", {
        "fonte": "DIEESE — Salário mínimo nominal e necessário",
        "fonte_url": URL_SALARIO,
        "colunas": ["mes", "minimo", "necessario"],
        "serie": pontos,
        "atualizado": pontos[-1][0],
    })
    return pontos[-1][0]


def coletar_cesta():
    """Preço e gasto mensal por produto e capital.

    A consulta do DIEESE é um formulário; o endereço e os campos são lidos de
    descobertas/dieese_cesta.html. Enquanto não estiverem confirmados, mantém o arquivo atual.
    """
    atual = ler_json("cesta")
    if atual is None:
        raise RuntimeError("coleta da cesta ainda não configurada (aguardando descoberta do formulário)")
    return atual.get("atualizado")


if __name__ == "__main__":
    print(coletar_salario())
