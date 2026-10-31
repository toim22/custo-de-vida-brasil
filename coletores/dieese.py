"""DIEESE: salário mínimo nominal e necessário (mensal) e Pesquisa Nacional da Cesta Básica (mensal)."""
import io
import re

import pandas as pd

from comum import DESCOBERTAS, INICIO, SESSAO, UF_REGIAO, baixar, norm, salvar_json, serie_ordenada

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


URL_CESTA = "https://www.dieese.org.br/cesta/cidade"
# código da cidade no formulário do DIEESE -> UF da capital
CIDADES = {
    "16": "SE", "13": "PA", "2": "MG", "22": "RR", "9": "DF", "19": "MS", "25": "MT", "4": "PR", "1": "SC",
    "11": "CE", "10": "GO", "3": "PB", "21": "AP", "28": "AL", "17": "AM", "15": "RN", "26": "TO", "5": "RS",
    "23": "RO", "12": "PE", "20": "AC", "6": "RJ", "7": "BA", "27": "MA", "8": "SP", "24": "PI", "14": "ES",
}
TIPOS = {"5": "gasto", "3": "horas", "4": "preco"}
ITENS = {
    "carne": ("Carne bovina de primeira", "kg"), "leite": ("Leite integral", "litro"), "feijao": ("Feijão", "kg"),
    "arroz": ("Arroz", "kg"), "farinha": ("Farinha (trigo ou mandioca)", "kg"), "batata": ("Batata", "kg"),
    "tomate": ("Tomate", "kg"), "pao": ("Pão francês", "kg"), "cafe": ("Café em pó", "kg"),
    "banana": ("Banana", "dúzia"), "acucar": ("Açúcar", "kg"), "oleo": ("Óleo de soja", "900 ml"),
    "manteiga": ("Manteiga", "kg"),
}
MESES_CURTOS = {m: i + 1 for i, m in enumerate(["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"])}


def chave_produto(nome):
    n = norm(nome)
    if n.startswith("total"):
        return "total"
    for k in ITENS:
        if n.startswith(k) or n.startswith(norm(ITENS[k][0]).split(" ")[0]):
            return k
    return None


def chave_mes(txt):
    t = norm(txt).replace("-", "/").replace(" ", "")
    m = re.fullmatch(r"(\d{1,2})/(\d{4})", t)
    if m:
        return f"{m.group(2)}-{int(m.group(1)):02d}"
    m = re.fullmatch(r"(\d{4})/(\d{1,2})", t)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}"
    m = re.fullmatch(r"([a-z]{3})[a-z]*/(\d{2,4})", t)
    if m and m.group(1) in MESES_CURTOS:
        ano = int(m.group(2))
        ano = ano + 2000 if ano < 100 else ano
        return f"{ano}-{MESES_CURTOS[m.group(1)]:02d}"
    m = re.fullmatch(r"(\d{2})(\d{4})", t)
    if m and 1 <= int(m.group(1)) <= 12:
        return f"{m.group(2)}-{m.group(1)}"
    return None


def numero_br(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return None if v != v else float(v)
    s = str(v).strip()
    h = re.fullmatch(r"(\d+)\s*h\s*(\d+)\s*m(in)?", norm(s))
    if h:
        return int(h.group(1)) + int(h.group(2)) / 60
    s = s.replace("R$", "").replace(" ", "")
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def ler_tabela_cidade(html):
    """Devolve {produto: {mes: valor}} lendo a tabela em qualquer orientação (meses nas linhas ou nas colunas)."""
    tabelas = pd.read_html(io.StringIO(html), thousands=None, decimal=".")
    saida = {}
    for t in tabelas:
        t = t.astype(str)
        cols = [str(c) if not isinstance(c, tuple) else str(c[-1]) for c in t.columns]
        if all(c.isdigit() for c in cols) and len(t) > 1:
            # tabela sem <th>: a primeira linha é o cabeçalho
            cols = [str(v) for v in t.iloc[0].tolist()]
            t = t.iloc[1:].reset_index(drop=True)
        # meses nas linhas, produtos nas colunas
        if sum(1 for v in t.iloc[:, 0] if chave_mes(v)) >= 1 and any(chave_produto(c) for c in cols[1:]):
            for _, linha in t.iterrows():
                mes = chave_mes(linha.iloc[0])
                if not mes:
                    continue
                for c, v in zip(cols[1:], linha.iloc[1:]):
                    k = chave_produto(c)
                    x = numero_br(v)
                    if k and x is not None:
                        saida.setdefault(k, {})[mes] = x
        # produtos nas linhas, meses nas colunas
        elif any(chave_mes(c) for c in cols[1:]):
            for _, linha in t.iterrows():
                k = chave_produto(linha.iloc[0])
                if not k:
                    continue
                for c, v in zip(cols[1:], linha.iloc[1:]):
                    mes = chave_mes(c)
                    x = numero_br(v)
                    if mes and x is not None:
                        saida.setdefault(k, {})[mes] = x
    return saida


def texto(r):
    try:
        return r.content.decode("utf-8")
    except UnicodeDecodeError:
        return r.content.decode("latin-1")


def coletar_cesta():
    """Preço médio, gasto mensal e tempo de trabalho por produto e capital, desde jan/2023."""
    from datetime import date
    hoje = date.today()
    fim = f"{hoje.month:02d}{hoje.year}"
    ini = INICIO[5:7] + INICIO[:4]
    capitais = {}
    amostra_salva = False
    for cod, uf in CIDADES.items():
        for tipo, nome_tipo in TIPOS.items():
            dados = {"farinha": "true", "cidades": cod, "tipoDado": tipo, "produtos": "0", "dataInicial": ini, "dataFinal": fim}
            try:
                r = SESSAO.post(URL_CESTA, data=dados, timeout=(15, 60))
                r.raise_for_status()
            except Exception as e:  # noqa: BLE001
                print(f"    POST falhou {uf} tipo {tipo}: {e}", flush=True)
                continue
            html = texto(r)
            if not amostra_salva:
                DESCOBERTAS.mkdir(exist_ok=True)
                (DESCOBERTAS / "dieese_resposta_exemplo.html").write_text(html, encoding="utf-8")
                amostra_salva = True
            tab = ler_tabela_cidade(html)
            print(f"    {uf} {nome_tipo}: {len(tab)} produtos, {sum(len(v) for v in tab.values())} valores", flush=True)
            for prod, meses in tab.items():
                capitais.setdefault(uf, {}).setdefault(prod, {}).setdefault(nome_tipo, {}).update(meses)
    if not capitais:
        raise RuntimeError("nenhum dado da cesta foi lido (ver descobertas/dieese_resposta_exemplo.html)")

    saida_cap = {}
    for uf, prods in capitais.items():
        tot = prods.get("total", {})
        item = {}
        for k in ITENS:
            if k in prods:
                item[k] = {t: serie_ordenada(v) for t, v in prods[k].items()}
        saida_cap[uf] = {
            "nome": NOME_CAPITAL[uf],
            "total": serie_ordenada(tot.get("gasto", {})),
            "horas": serie_ordenada(tot.get("horas", {})),
            "itens": item,
        }

    # Brasil e regiões: média simples das capitais
    grupos = {"BR": list(saida_cap)}
    for uf in saida_cap:
        grupos.setdefault(UF_REGIAO[uf], []).append(uf)
    agregados = {}
    for g, ufs in grupos.items():
        def media_serie(pega):
            acc = {}
            for uf in ufs:
                for m, v in pega(saida_cap[uf]) or []:
                    acc.setdefault(m, []).append(v)
            return [[m, round(sum(v) / len(v), 2)] for m, v in sorted(acc.items())]
        agregados[g] = {
            "total": media_serie(lambda c: c["total"]),
            "horas": media_serie(lambda c: c["horas"]),
            "itens": {k: {t: media_serie(lambda c, k=k, t=t: c["itens"].get(k, {}).get(t)) for t in ("gasto", "preco")} for k in ITENS},
            "capitais": len(ufs),
        }

    ult = max((c["total"][-1][0] for c in saida_cap.values() if c["total"]), default=None)
    salvar_json("cesta", {
        "fonte": "DIEESE — Pesquisa Nacional da Cesta Básica de Alimentos",
        "fonte_url": "https://www.dieese.org.br/cesta/",
        "itens": {k: {"nome": v[0], "unidade": v[1]} for k, v in ITENS.items()},
        "capitais": saida_cap,
        "agregados": agregados,
        "atualizado": ult,
    })
    return ult


NOME_CAPITAL = {
    "SE": "Aracaju", "PA": "Belém", "MG": "Belo Horizonte", "RR": "Boa Vista", "DF": "Brasília",
    "MS": "Campo Grande", "MT": "Cuiabá", "PR": "Curitiba", "SC": "Florianópolis", "CE": "Fortaleza",
    "GO": "Goiânia", "PB": "João Pessoa", "AP": "Macapá", "AL": "Maceió", "AM": "Manaus", "RN": "Natal",
    "TO": "Palmas", "RS": "Porto Alegre", "RO": "Porto Velho", "PE": "Recife", "AC": "Rio Branco",
    "RJ": "Rio de Janeiro", "BA": "Salvador", "MA": "São Luís", "SP": "São Paulo", "PI": "Teresina",
    "ES": "Vitória",
}


if __name__ == "__main__":
    print(coletar_salario())
