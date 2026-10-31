"""IBGE: IPCA mensal (variação por subitem e por região metropolitana).

A variação oficial de cada item é usada para atualizar, mês a mês, o preço de partida
dos itens avulsos e do Churrasco pra 6 (ver calculos.py), e para a "inflação da comida em casa".
"""
from comum import DESCOBERTAS, INICIO, baixar, config, norm, salvar_json

API = "https://apisidra.ibge.gov.br/values"
UF_IBGE = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP", "17": "TO",
    "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB", "26": "PE", "27": "AL", "28": "SE", "29": "BA",
    "31": "MG", "32": "ES", "33": "RJ", "35": "SP", "41": "PR", "42": "SC", "43": "RS",
    "50": "MS", "51": "MT", "52": "GO", "53": "DF",
}
FIXOS = {"geral": ["Índice geral"], "comida_em_casa": ["Alimentação no domicílio"]}


def categorias_ipca():
    # A API de metadados (servicodados) não responde a partir do GitHub; a apisidra sim.
    # Pedimos o último mês do Brasil com todas as categorias e lemos código e nome de cada uma.
    linhas = baixar(f"{API}/t/7060/n1/all/v/63/p/last/c315/all").json()[1:]
    por_nome = {}
    for l in linhas:
        nome = norm(l.get("D4N", ""))
        nome = nome.split(".", 1)[1].strip() if nome[:1].isdigit() and "." in nome else nome
        if l.get("D4C", "").isdigit():
            por_nome.setdefault(nome, int(l["D4C"]))
    print(f"  {len(por_nome)} categorias do IPCA lidas")
    try:
        DESCOBERTAS.mkdir(exist_ok=True)
        (DESCOBERTAS / "ipca_categorias.txt").write_text(
            "\n".join(f"{i}\t{n}" for n, i in sorted(por_nome.items(), key=lambda x: x[1])), encoding="utf-8")
    except OSError:
        pass
    return 315, por_nome


def escolher(por_nome, candidatos):
    for c in candidatos:
        if norm(c) in por_nome:
            return por_nome[norm(c)], c
    return None, None


def coletar():
    cfg = config("itens")
    pedidos = dict(FIXOS)
    for chave, it in cfg["avulsos"].items():
        pedidos[chave] = it["ipca"]
    for chave, it in cfg["churrasco"]["extras"].items():
        pedidos[chave] = it["ipca"]

    classe, por_nome = categorias_ipca()
    escolhidos = {}
    for chave, cands in pedidos.items():
        cid, nome = escolher(por_nome, cands)
        if cid is None:
            print(f"  aviso: nenhum subitem do IPCA encontrado para {chave} ({cands})")
            continue
        escolhidos[chave] = {"id": cid, "nome_ibge": nome}

    ids = sorted({v["id"] for v in escolhidos.values()})
    inicio = INICIO[:4] + INICIO[5:7]
    url = f"{API}/t/7060/n1/all/n7/all/n6/all/v/63/p/{inicio}-209912/c{classe}/{','.join(str(i) for i in ids)}"
    linhas = baixar(url).json()[1:]
    por_id = {}
    for l in linhas:
        try:
            v = float(l["V"])
        except (TypeError, ValueError):
            continue
        cod = l["D1C"]
        local = "BR" if l["NC"] == "1" else UF_IBGE.get(cod[:2])
        if not local:
            continue
        per = l["D3C"]
        mes = f"{per[:4]}-{per[4:6]}"
        cat = next((l[k] for k in ("D4C", "D5C") if k in l and l[k] and l[k].isdigit() and int(l[k]) in ids), None)
        if cat is None:
            continue
        por_id.setdefault(int(cat), {}).setdefault(local, {})[mes] = v

    series = {}
    for chave, info in escolhidos.items():
        locais = por_id.get(info["id"], {})
        series[chave] = {loc: sorted([[m, v] for m, v in pts.items()]) for loc, pts in sorted(locais.items())}
    ult = max((pts[-1][0] for s in series.values() for pts in s.values() if pts), default=None)
    salvar_json("ipca", {
        "fonte": "IBGE — IPCA, tabela 7060 (variação mensal, %)",
        "fonte_url": "https://sidra.ibge.gov.br/tabela/7060",
        "categorias": escolhidos,
        "series": series,
        "atualizado": ult,
    })
    return ult


if __name__ == "__main__":
    print(coletar())
