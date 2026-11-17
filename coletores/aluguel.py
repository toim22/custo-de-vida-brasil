"""Aluguel: quanto o aluguel subiu desde janeiro de 2023 e quanto custa alugar hoje.

Três fontes abertas, cada uma responde uma pergunta:
1. IBGE, IPCA subitem "Aluguel residencial" (tabela 7060): quanto subiu o aluguel que as
   famílias pagam de fato (contratos em andamento), por região metropolitana/capital. Mensal.
2. Banco Central (SGS): IGP-M (série 189) e IPCA (série 433). São os índices usados para
   reajustar contratos; mostramos o acumulado de 12 meses de cada mês.
3. FipeZap, preço médio pedido em anúncios de aluguel (R$ por m²) em cerca de 25 cidades.
   É a única fonte aberta com preço em reais. Se a planilha mudar de formato, as outras
   duas partes continuam funcionando e o problema fica registrado em descobertas/.
"""
import io
import re
from datetime import date, datetime

from comum import CAPITAL_UF, REGIAO_NOMES, UF_NOMES, UF_REGIAO, DESCOBERTAS, INICIO, baixar, ler_json, norm, salvar_json
from ibge import API, UF_IBGE

IPCA_ALUGUEL = 7448   # 2101001.Aluguel residencial
IPCA_GERAL = 7169     # Índice geral
SGS = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{}/dados?formato=json&dataInicial={}&dataFinal={}"
IPEA = "http://www.ipeadata.gov.br/api/odata4/ValoresSerie(SERCODIGO='{}')"
# (chave, código no Ipeadata, série no SGS do Banco Central). O Ipeadata responde a partir do GitHub;
# o SGS às vezes devolve "Requisição inválida" para servidores fora do Brasil e fica como reserva.
REAJUSTE = (("igpm", "IGP12_IGPMG12", 189), ("ipca", "PRECOS12_IPCAG12", 433))
FIPEZAP_URL = "https://downloads.fipe.org.br/indices/fipezap/fipezap-serieshistoricas.xlsx"
AREA_REFERENCIA = 60  # m², apartamento de 2 quartos típico


def _mes_inicio():
    return INICIO[:7]


def _anotar(nome, texto):
    try:
        DESCOBERTAS.mkdir(exist_ok=True)
        (DESCOBERTAS / nome).write_text(texto, encoding="utf-8")
    except OSError:
        pass


def indice_acumulado(variacoes):
    """[[mes, var%], ...] -> [[mes, índice]] com base 100 no mês anterior ao primeiro."""
    f, saida = 100.0, []
    for mes, v in variacoes:
        f *= 1 + v / 100
        saida.append([mes, round(f, 3)])
    return saida


def acumulado_12m(variacoes, desde):
    """[[mes, var%], ...] -> [[mes, acumulado 12 meses %]] a partir de `desde`."""
    saida = []
    for i in range(11, len(variacoes)):
        if variacoes[i][0] < desde:
            continue
        janela = variacoes[i - 11:i + 1]
        meses = [int(m[:4]) * 12 + int(m[5:]) for m, _ in janela]
        if meses[-1] - meses[0] != 11:  # mês faltando: não inventa
            continue
        f = 1.0
        for _, v in janela:
            f *= 1 + v / 100
        saida.append([variacoes[i][0], round((f - 1) * 100, 2)])
    return saida


# ---------- 1. IPCA aluguel residencial ----------
def coletar_ipca():
    ini = _mes_inicio().replace("-", "")
    url = f"{API}/t/7060/n1/all/n7/all/n6/all/v/63/p/{ini}-209912/c315/{IPCA_ALUGUEL},{IPCA_GERAL}"
    linhas = baixar(url).json()[1:]
    por = {IPCA_ALUGUEL: {}, IPCA_GERAL: {}}
    nomes = {}
    for l in linhas:
        try:
            v = float(l["V"])
        except (TypeError, ValueError):
            continue
        cod = l["D1C"]
        local = "BR" if l["NC"] == "1" else UF_IBGE.get(cod[:2])
        if not local:
            continue
        cat = next((int(l[k]) for k in ("D4C", "D5C") if l.get(k, "").isdigit() and int(l[k]) in por), None)
        if cat is None:
            continue
        per = l["D3C"]
        por[cat].setdefault(local, {})[f"{per[:4]}-{per[4:6]}"] = v
        nomes[local] = l.get("D1N", local)
    if not por[IPCA_ALUGUEL].get("BR"):
        raise RuntimeError("IPCA: o subitem Aluguel residencial veio vazio")

    locais = {}
    for local in sorted(por[IPCA_ALUGUEL]):
        var = sorted([m, x] for m, x in por[IPCA_ALUGUEL][local].items())
        geral = sorted([m, x] for m, x in por[IPCA_GERAL].get(local, {}).items())
        locais[local] = {
            "area_ibge": "Brasil" if local == "BR" else nomes.get(local, local),
            "fonte": "ipca",
            "variacao": var,
            "indice": indice_acumulado(var),
            "indice_geral": indice_acumulado(geral),
        }
    return locais


# ---------- 2. IGP-M e IPCA para reajuste de contrato ----------
def _mensal_ipea(codigo, desde):
    var = []
    for d in baixar(IPEA.format(codigo)).json()["value"]:
        mes = str(d.get("VALDATA", ""))[:7]
        if mes >= desde and d.get("VALVALOR") is not None:
            var.append([mes, float(d["VALVALOR"])])
    return sorted(var)


def _mensal_sgs(serie, desde):
    ini = f"01/{desde[5:7]}/{desde[:4]}"
    fim = date.today().strftime("%d/%m/%Y")
    var = []
    for d in baixar(SGS.format(serie, ini, fim), tentativas=2).json():
        _, mes, ano = d["data"].split("/")
        var.append([f"{ano}-{mes}", float(d["valor"])])
    return sorted(var)


def coletar_reajuste():
    desde = f"{int(INICIO[:4]) - 1}-01"  # um ano antes, para o acumulado de jan/2023
    saida, erros = {}, []
    for chave, ipea, sgs in REAJUSTE:
        for nome, func, cod in (("Ipeadata", _mensal_ipea, ipea), ("Banco Central", _mensal_sgs, sgs)):
            try:
                serie = acumulado_12m(func(cod, desde), _mes_inicio())
            except Exception as e:  # noqa: BLE001
                erros.append(f"{nome} {cod}: {e}"[:150])
                continue
            if serie:
                saida[chave] = serie
                break
        if chave not in saida:
            raise RuntimeError(f"{chave} sem dados: " + "; ".join(erros))
    return saida


# ---------- 3. FipeZap: preço do aluguel anunciado ----------
def _mes_de(valor):
    if isinstance(valor, (datetime, date)):
        return f"{valor.year:04d}-{valor.month:02d}"
    m = re.match(r"^(\d{4})-(\d{2})", str(valor))
    return f"{m.group(1)}-{m.group(2)}" if m else None


def _rotulos(df, n=8):
    """Junta as primeiras linhas (cabeçalhos em vários níveis) num rótulo por coluna,
    repetindo para a direita o texto de células mescladas."""
    rot = [""] * df.shape[1]
    for i in range(min(n, len(df))):
        anterior = ""
        for j in range(df.shape[1]):
            v = df.iat[i, j]
            txt = "" if v is None or str(v) == "nan" or isinstance(v, (int, float, datetime, date)) else str(v)
            if txt:
                anterior = txt
            elif i < 3:  # só os níveis de cima costumam ser mesclados
                txt = anterior
            if txt:
                rot[j] = (rot[j] + " | " + txt).strip(" |")
    return rot


def _coluna_preco_locacao(rot):
    candidatas = []
    for j, r in enumerate(rot):
        n = norm(r)
        if "residenc" not in n or "comerc" in n:
            continue
        if "loca" in n and "preco medio" in n and "venda" not in n.split("loca")[-1]:
            candidatas.append((("total" in n) * 2 - bool(re.search(r"\b[1-4]\s*(d|dorm|quarto)", n)), -j))
    return -max(candidatas)[1] if candidatas else None


# Cidades do FipeZap que não são capitais
OUTRAS_UF = {
    "SP": ["barueri", "campinas", "diadema", "guaruja", "guarulhos", "osasco", "praia grande", "ribeirao preto",
           "santo andre", "santos", "sao bernardo do campo", "sao caetano do sul", "sao jose do rio preto",
           "sao jose dos campos", "sao vicente", "sorocaba", "jundiai", "mogi das cruzes"],
    "RJ": ["niteroi"], "MG": ["betim", "contagem", "juiz de fora", "uberlandia"], "ES": ["vila velha", "serra"],
    "RS": ["canoas", "caxias do sul", "novo hamburgo", "pelotas", "santa maria", "sao leopoldo"],
    "PR": ["londrina", "sao jose dos pinhais", "maringa"],
    "SC": ["balneario camboriu", "blumenau", "itajai", "itapema", "joinville", "sao jose"],
    "PE": ["jaboatao dos guararapes"],
}
NOME_MEDIA = "Média das cidades do FipeZap"


def _uf_cidade(nome):
    n = norm(nome)
    if n in CAPITAL_UF:
        return CAPITAL_UF[n]
    for uf, cidades in OUTRAS_UF.items():
        if n in cidades:
            return uf
    m = re.search(r"\(([A-Za-z]{2})\)\s*$", nome) or re.search(r"[-–/]\s*([A-Za-z]{2})\s*$", nome)
    return m.group(1).upper() if m else None


def coletar_fipezap():
    import pandas as pd

    r = baixar(FIPEZAP_URL, timeout=(15, 120))
    planilhas = pd.read_excel(io.BytesIO(r.content), sheet_name=None, header=None)
    diag, cidades = [], {}
    for aba, df in planilhas.items():
        rot = _rotulos(df)
        col = _coluna_preco_locacao(rot)
        diag.append(f"== {aba}: coluna escolhida {col}\n" + "\n".join(f"  {j}: {x}" for j, x in enumerate(rot) if x))
        if col is None or norm(aba) in {"resumo", "aux", "notas", "sumario"}:
            continue
        col_data = next((j for j in range(df.shape[1]) if sum(_mes_de(v) is not None for v in df.iloc[:, j]) > 12), None)
        if col_data is None:
            continue
        pts = {}
        for i in range(len(df)):
            mes, v = _mes_de(df.iat[i, col_data]), df.iat[i, col]
            try:
                v = float(v)
            except (TypeError, ValueError):
                continue
            if mes and mes >= _mes_inicio() and 5 < v < 500:  # R$/m² plausível para aluguel
                pts[mes] = round(v, 2)
        if len(pts) >= 6:
            nome = str(aba).strip()
            media = norm(nome) in {"indice fipezap", "fipezap"}
            cidades[NOME_MEDIA if media else nome] = {
                "uf": None if media else _uf_cidade(nome),
                "capital": norm(nome) in CAPITAL_UF,
                "media": media,
                "preco_m2": sorted([m, x] for m, x in pts.items()),
            }
    _anotar("fipezap_cabecalhos.txt", "\n\n".join(diag))
    if not cidades:
        raise RuntimeError("FipeZap: nenhuma cidade com preço de locação reconhecido (veja descobertas/fipezap_cabecalhos.txt)")
    return cidades


# ---------- 4. Regiões e os 27 estados ----------
def _media_mensal(series):
    """Média simples, mês a mês, de várias séries [[mes, var%]]. Só usa meses que todas têm."""
    dicts = [dict(s) for s in series if s]
    if not dicts:
        return []
    meses = sorted(set.intersection(*(set(d) for d in dicts)))
    return [[m, round(sum(d[m] for d in dicts) / len(dicts), 4)] for m in meses]


def _var_de_precos(precos):
    """[[mes, R$/m²]] -> [[mes, var%]] (o primeiro mês vira a base)."""
    return [[precos[i][0], round((precos[i][1] / precos[i - 1][1] - 1) * 100, 4)] for i in range(1, len(precos))]


def _com_base(var, base_mes):
    """Índice com 100 no mês base (que entra como primeiro ponto)."""
    return [[base_mes, 100.0]] + indice_acumulado(var)


def completar_locais(ipca, fipezap):
    """Acrescenta as 5 regiões e os estados que o IPCA não cobre.

    Regiões: média simples, mês a mês, das áreas do IPCA daquela região.
    Estado sem IPCA: variação do preço anunciado na capital (FipeZap), se houver.
    Estado sem nenhuma pesquisa: repete a região, com aviso claro.
    """
    locais = dict(ipca)
    ufs_ipca = [u for u in ipca if u in UF_REGIAO]
    for reg, nome in REGIAO_NOMES.items():
        ufs = [u for u in ufs_ipca if UF_REGIAO[u] == reg]
        if not ufs:
            continue
        var = _media_mensal([ipca[u]["variacao"] for u in ufs])
        geral = _media_mensal([[[m, v] for m, v in _vars_do_indice(ipca[u]["indice_geral"])] for u in ufs])
        cidades = ", ".join(ipca[u]["area_ibge"].split(" - ")[0] for u in sorted(ufs))
        locais[reg] = {
            "area_ibge": nome, "fonte": "media", "variacao": var,
            "indice": indice_acumulado(var), "indice_geral": indice_acumulado(geral),
            "aviso": f"Média das áreas pesquisadas pelo IBGE na região: {cidades}.",
        }
    capital_de = {uf: c for c, v in fipezap.items() if v.get("capital") and (uf := v.get("uf"))}
    for uf, nome_uf in UF_NOMES.items():
        if uf in locais:
            continue
        reg = locais.get(UF_REGIAO[uf], {})
        cidade = capital_de.get(uf)
        if cidade and len(fipezap[cidade]["preco_m2"]) >= 13:
            precos = fipezap[cidade]["preco_m2"]
            var = _var_de_precos(precos)
            locais[uf] = {
                "area_ibge": f"{cidade} - {uf}", "fonte": "fipezap", "variacao": var,
                "indice": _com_base(var, precos[0][0]), "indice_geral": reg.get("indice_geral", []),
                "aviso": f"O IBGE não pesquisa aluguel {_em(uf)}. Usamos o preço dos anúncios de aluguel em {cidade} (FipeZap), desde {precos[0][0][5:]}/{precos[0][0][:4]}.",
            }
        elif reg:
            locais[uf] = {
                "area_ibge": f"{nome_uf} (média do {REGIAO_NOMES[UF_REGIAO[uf]]})", "fonte": "regiao",
                "variacao": reg["variacao"], "indice": reg["indice"], "indice_geral": reg["indice_geral"],
                "aviso": f"Nenhuma pesquisa oficial ou de anúncios cobre aluguel {_em(uf)}. Mostramos a média da região {REGIAO_NOMES[UF_REGIAO[uf]]}.",
            }
    return locais


def _em(uf):
    """'no Amapá', 'na Paraíba', 'em Alagoas'."""
    nome = UF_NOMES[uf]
    if uf in {"AC", "AM", "AP", "CE", "DF", "ES", "MA", "MT", "MS", "PA", "PR", "PI", "RJ", "RN", "RS", "TO"}:
        return "no " + nome
    return ("na " if uf in {"BA", "PB"} else "em ") + nome


def _vars_do_indice(indice):
    """Índice base 100 (mês anterior ao primeiro ponto) -> variações mensais."""
    saida, ant = [], 100.0
    for m, v in indice:
        saida.append([m, (v / ant - 1) * 100])
        ant = v
    return saida


def coletar():
    anterior = ler_json("aluguel", {}) or {}
    avisos = []
    ipca = coletar_ipca()
    try:
        reajuste = coletar_reajuste()
    except Exception as e:  # noqa: BLE001
        avisos.append(f"Banco Central: {e}"[:300])
        reajuste = {k: v for k, v in anterior.get("reajuste", {}).items() if k in ("igpm", "ipca")}
    try:
        fipezap = coletar_fipezap()
    except Exception as e:  # noqa: BLE001
        avisos.append(f"FipeZap: {e}"[:300])
        fipezap = anterior.get("fipezap", {}).get("cidades", {})  # mantém o último dado bom
    for a in avisos:
        print("  aviso:", a)

    ult = ipca["BR"]["variacao"][-1][0]
    salvar_json("aluguel", {
        "ipca": {
            "fonte": "IBGE — IPCA, tabela 7060, subitem 2101001 Aluguel residencial (variação mensal, %)",
            "fonte_url": "https://sidra.ibge.gov.br/tabela/7060",
            "base": "índice 100 = dezembro de 2022",
            "locais": completar_locais(ipca, fipezap),
        },
        "reajuste": {
            "fonte": "Banco Central, SGS: IGP-M (série 189) e IPCA (série 433), acumulado em 12 meses (%)",
            "fonte_url": "https://www3.bcb.gov.br/sgspub/",
            **reajuste,
        },
        "fipezap": {
            "fonte": "Índice FipeZap de Locação Residencial — preço médio anunciado (R$/m²)",
            "fonte_url": "https://www.fipe.org.br/pt-br/indices/fipezap/",
            "area_referencia_m2": AREA_REFERENCIA,
            "cidades": fipezap,
        },
        "avisos": avisos,
        "atualizado": ult,
    })
    if avisos:  # dados bons já gravados; a falha é só para o GitHub avisar
        raise RuntimeError("; ".join(avisos))
    return ult


if __name__ == "__main__":
    print(coletar())
