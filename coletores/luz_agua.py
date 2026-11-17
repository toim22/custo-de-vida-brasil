"""Conta de luz e conta de água por estado, região e Brasil.

Luz: tarifa residencial (B1, convencional) da distribuidora que atende a capital, publicada
pela ANEEL, mais a bandeira tarifária do mês e os impostos estimados (config/energia.json).
Água: tarifa de referência de cada estado (config/agua.json) corrigida mês a mês pela variação
oficial do IPCA "taxa de água e esgoto" (local onde o IBGE pesquisa, Brasil nos demais).
Também grava a inflação oficial (IPCA) da energia e da água, por local.

Roda sozinho (python luz_agua.py) e grava o resultado em dados/estado.json, como rodar.py.
"""
import csv
import io
import json
import sys
import traceback
from datetime import date, datetime, timezone

from comum import DESCOBERTAS, INICIO, UF_REGIAO, baixar, config, ler_json, media, norm, salvar_json
from ibge import API, UF_IBGE

CKAN = "https://dadosabertos.aneel.gov.br/api/3/action"
IPCA_IDS = {"energia": 7484, "agua": 7451}  # subitens do IPCA (tabela 7060, classificação 315)


def guardar(nome, texto):
    try:
        DESCOBERTAS.mkdir(exist_ok=True)
        (DESCOBERTAS / nome).write_text(texto, encoding="utf-8")
    except OSError:
        pass


def num(txt):
    if txt is None:
        return None
    t = str(txt).strip().replace(" ", "")
    if not t:
        return None
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None


def dia(txt):
    t = str(txt or "").strip()[:10]
    for f in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(t, f).date()
        except ValueError:
            pass
    return None


def meses(desde, ate):
    a, m = int(desde[:4]), int(desde[5:7])
    while f"{a:04d}-{m:02d}" <= ate:
        yield f"{a:04d}-{m:02d}"
        m += 1
        if m == 13:
            a, m = a + 1, 1


def mes_atual():
    return date.today().strftime("%Y-%m")


# ---------------------------------------------------------------- ANEEL (CKAN)

def recursos(pacote):
    j = baixar(f"{CKAN}/package_show?id={pacote}").json()
    return j["result"]["resources"]


def linhas_ckan(rec, filtros=None):
    """Lê as linhas de um recurso: pela API (datastore) quando existe, senão baixa o CSV."""
    if rec.get("datastore_active"):
        try:
            out, offset = [], 0
            while True:
                url = f"{CKAN}/datastore_search?resource_id={rec['id']}&limit=32000&offset={offset}"
                if filtros:
                    url += "&filters=" + json.dumps(filtros, ensure_ascii=False)
                res = baixar(url, timeout=(15, 180)).json()["result"]
                out.extend(res["records"])
                offset += len(res["records"])
                if not res["records"] or offset >= res.get("total", 0):
                    return out
        except Exception as e:  # noqa: BLE001
            print("  datastore falhou, baixando o CSV:", e)
    r = baixar(rec["url"], timeout=(15, 600), stream=True)
    bruto = r.content
    try:
        texto = bruto.decode("utf-8-sig")
    except UnicodeDecodeError:
        texto = bruto.decode("latin-1")
    amostra = texto[:5000]
    sep = ";" if amostra.count(";") > amostra.count(",") else ","
    leitor = csv.DictReader(io.StringIO(texto), delimiter=sep)
    out = []
    for l in leitor:
        if filtros and any(norm(l.get(k)) != norm(v) for k, v in filtros.items()):
            continue
        out.append(l)
    return out


def campo(linha, *nomes):
    for n in nomes:
        for k in linha:
            if norm(k) == norm(n):
                return linha[k]
    return None


def tarifas_residenciais():
    """{SigAgente: [(inicio, fim, R$/kWh sem impostos), ...]} da tarifa B1 residencial convencional."""
    recs = recursos("tarifas-distribuidoras-energia-eletrica")
    guardar("aneel_tarifas_recursos.txt", "\n".join(f"{r.get('id')}\t{r.get('format')}\t{r.get('datastore_active')}\t{r.get('name')}\t{r.get('url')}" for r in recs))
    csvs = [r for r in recs if "csv" in (r.get("format") or "").lower() or str(r.get("url", "")).lower().endswith(".csv")]
    rec = next((r for r in csvs if "homologad" in norm(r.get("name", "") + r.get("url", ""))), csvs[0] if csvs else None)
    if not rec:
        raise RuntimeError("ANEEL: recurso CSV de tarifas não encontrado")
    print("  recurso:", rec.get("name"), rec.get("url"))
    filtros = {"DscSubGrupo": "B1", "DscModalidadeTarifaria": "Convencional", "DscClasse": "Residencial"}
    linhas = linhas_ckan(rec, filtros)
    print(f"  {len(linhas)} linhas B1 residenciais convencionais")
    agentes, por_agente = set(), {}
    for l in linhas:
        ag = (campo(l, "SigAgente") or "").strip()
        agentes.add(ag)
        if norm(campo(l, "DscSubClasse")) != "residencial":
            continue
        base = norm(campo(l, "DscBaseTarifaria"))
        if base and "aplicacao" not in base:
            continue
        if norm(campo(l, "DscDetalhe")) not in ("", "nao se aplica"):
            continue
        posto = norm(campo(l, "NomPostoTarifario"))
        if posto not in ("", "nao se aplica"):
            continue
        ini, fim = dia(campo(l, "DatInicioVigencia")), dia(campo(l, "DatFimVigencia"))
        tusd, te = num(campo(l, "VlrTUSD")), num(campo(l, "VlrTE"))
        if not ini or tusd is None or te is None:
            continue
        valor = tusd + te
        unidade = norm(campo(l, "DscUnidadeTerciaria"))
        if "mwh" in unidade or valor > 20:
            valor /= 1000
        por_agente.setdefault(ag, {})[ini] = (ini, fim, valor)
    guardar("aneel_agentes.txt", "\n".join(sorted(agentes)))
    return {ag: sorted(v.values()) for ag, v in por_agente.items()}


def bandeiras():
    """{"AAAA-MM": (nome, adicional R$/kWh)}"""
    recs = recursos("bandeiras-tarifarias")
    guardar("aneel_bandeiras_recursos.txt", "\n".join(f"{r.get('id')}\t{r.get('format')}\t{r.get('datastore_active')}\t{r.get('name')}\t{r.get('url')}" for r in recs))
    csvs = [r for r in recs if "csv" in (r.get("format") or "").lower() or str(r.get("url", "")).lower().endswith(".csv")]
    rec = next((r for r in csvs if "acionamento" in norm(r.get("name", "") + r.get("url", ""))), csvs[0] if csvs else None)
    if not rec:
        raise RuntimeError("ANEEL: recurso de bandeiras não encontrado")
    out = {}
    for l in linhas_ckan(rec):
        d = dia(campo(l, "DatCompetencia"))
        nome = (campo(l, "NomBandeiraAcionada") or "").strip()
        v = num(campo(l, "VlrAdicionalBandeira"))
        if not d or not nome:
            continue
        v = v or 0.0
        if v > 1:  # R$/MWh -> R$/kWh
            v /= 1000
        out[d.strftime("%Y-%m")] = (nome, v)
    return out


def escolher_agentes(tarifas, candidatos):
    nomes = {norm(a): a for a in tarifas}
    achados = [nomes[norm(c)] for c in candidatos if norm(c) in nomes]
    if not achados:
        achados = [a for a in tarifas if any(norm(a).startswith(norm(c) + " ") or norm(a).startswith(norm(c) + "-") for c in candidatos[:2])]
    return list(dict.fromkeys(achados))


def tarifa_no_dia(periodos, d):
    vale = [p for p in periodos if p[0] <= d and (p[1] is None or p[1] >= d)]
    if not vale:
        vale = [p for p in periodos if p[0] <= d]
    return max(vale)[2] if vale else None


def grupos(series):
    """Regiões e Brasil (média simples dos estados). "SE" é Sergipe e também Sudeste: o estado vence."""
    ufs = [u for u in series if u in UF_REGIAO]
    out = [(r, [u for u in ufs if UF_REGIAO[u] == r]) for r in sorted(set(UF_REGIAO.values())) if r not in UF_REGIAO]
    return out + [("BR", ufs)]


def coletar_energia():
    cfg = config("energia")
    tarifas = tarifas_residenciais()
    try:
        band = bandeiras()
    except Exception as e:  # noqa: BLE001
        print("  aviso: bandeiras indisponíveis:", e)
        band = {}
    fim = mes_atual()
    kwh, pis = cfg["kwh_mes"], cfg["pis_cofins"]
    series, info = {}, {}
    for uf, e in cfg["estados"].items():
        ags = escolher_agentes(tarifas, e["distribuidora"])
        if not ags:
            print(f"  aviso: distribuidora de {uf} não encontrada ({e['distribuidora']})")
            continue
        periodos = sorted(p for a in ags for p in tarifas[a])
        tar, conta = [], []
        for m in meses(INICIO[:7], fim):
            t = tarifa_no_dia(periodos, date(int(m[:4]), int(m[5:7]), 15))
            if t is None:
                continue
            adic = band.get(m, (None, 0.0))[1]
            tar.append([m, round(t, 5)])
            conta.append([m, round(kwh * (t + adic) / (1 - e["icms"] - pis), 2)])
        ultimos = [p for p in periodos if p[0] <= date.today()]
        reaj = None
        if len(ultimos) >= 2 and ultimos[-2][2]:
            reaj = {"data": ultimos[-1][0].isoformat(), "pct": round((ultimos[-1][2] / ultimos[-2][2] - 1) * 100, 2)}
        series[uf] = {"tarifa": tar, "conta": conta}
        info[uf] = {"distribuidora": ags[-1], "icms": e["icms"], "ultimo_reajuste": reaj}
    # Regiões e Brasil: média simples dos estados
    for grupo, ufs in grupos(series):
        if not ufs:
            continue
        agg = {}
        for k in ("tarifa", "conta"):
            todos = sorted({m for u in ufs for m, _ in series[u][k]})
            agg[k] = [[m, round(media([dict(series[u][k]).get(m) for u in ufs]), 5 if k == "tarifa" else 2)] for m in todos]
        series[grupo] = agg
    salvar_json("energia", {
        "fonte": "ANEEL — tarifas homologadas das distribuidoras e bandeiras tarifárias (dados abertos)",
        "fonte_url": "https://dadosabertos.aneel.gov.br/dataset/tarifas-distribuidoras-energia-eletrica",
        "kwh_mes": kwh, "pis_cofins": pis,
        "bandeiras": [[m, n, round(v, 5)] for m, (n, v) in sorted(band.items()) if m >= INICIO[:7]],
        "estados": info,
        "series": series,
        "atualizado": max((s["conta"][-1][0] for s in series.values() if s.get("conta")), default=None),
    })
    if not series:
        raise RuntimeError("nenhuma distribuidora encontrada; veja descobertas/aneel_agentes.txt")
    return f"{len(info)} estados, bandeira {band.get(fim, ('?',))[0]}"


# ---------------------------------------------------------------- IPCA energia e água

def ipca_luz_agua(desde="2020-01"):
    ids = ",".join(str(i) for i in IPCA_IDS.values())
    url = f"{API}/t/7060/n1/all/n7/all/n6/all/v/63/p/{desde.replace('-', '')}-209912/c315/{ids}"
    out = {k: {} for k in IPCA_IDS}
    inv = {v: k for k, v in IPCA_IDS.items()}
    for l in baixar(url).json()[1:]:
        v = num(l.get("V"))
        if v is None:
            continue
        local = "BR" if l["NC"] == "1" else UF_IBGE.get(l["D1C"][:2])
        cat = next((l[k] for k in ("D4C", "D5C") if l.get(k, "").isdigit() and int(l[k]) in inv), None)
        if not local or cat is None:
            continue
        per = l["D3C"]
        out[inv[int(cat)]].setdefault(local, {})[f"{per[:4]}-{per[4:6]}"] = v
    return out


def coletar_agua(ipca):
    cfg = config("agua")
    ref, vol = cfg["ref"], cfg["m3_mes"]
    var = ipca["agua"]
    br = var.get("BR", {})
    ult = max(br) if br else ref
    series, info = {}, {}
    for uf, e in cfg["estados"].items():
        base = vol * (e["agua"] + e.get("esgoto", 0))
        local = uf if uf in var else "BR"
        v = var.get(local, {})
        valores = {ref: base}
        atual = base
        for m in meses(ref, ult):  # para frente
            if m == ref:
                continue
            atual *= 1 + (v.get(m, br.get(m, 0.0))) / 100
            valores[m] = atual
        atual = base
        for m in sorted((x for x in set(v) | set(br) if INICIO[:7] <= x <= ref), reverse=True):  # para trás
            if m == ref:
                continue
            nxt = f"{int(m[:4]) + (m[5:] == '12'):04d}-{(int(m[5:]) % 12) + 1:02d}"
            if nxt <= ref:
                atual /= 1 + (v.get(nxt, br.get(nxt, 0.0))) / 100
                valores[m] = atual
        series[uf] = {"conta": [[m, round(x, 2)] for m, x in sorted(valores.items()) if m >= INICIO[:7]]}
        info[uf] = {"empresa": e.get("empresa"), "ipca_local": local != "BR", "agua_m3": e["agua"], "esgoto_m3": e.get("esgoto", 0)}
    for grupo, ufs in grupos(series):
        if not ufs:
            continue
        todos = sorted({m for u in ufs for m, _ in series[u]["conta"]})
        series[grupo] = {"conta": [[m, round(media([dict(series[u]["conta"]).get(m) for u in ufs]), 2)] for m in todos]}
    salvar_json("agua", {
        "fonte": cfg["fonte"], "fonte_url": cfg.get("fonte_url"), "ref": ref, "m3_mes": vol,
        "estados": info, "series": series, "atualizado": ult,
    })
    return ult


def coletar_tudo():
    ipca = ipca_luz_agua()
    salvar_json("ipca_luz_agua", {
        "fonte": "IBGE — IPCA, tabela 7060 (variação mensal, %): energia elétrica residencial e taxa de água e esgoto",
        "fonte_url": "https://sidra.ibge.gov.br/tabela/7060",
        "series": {k: {loc: sorted([m, x] for m, x in pts.items() if m >= INICIO[:7]) for loc, pts in sorted(v.items())} for k, v in ipca.items()},
    })
    return ipca


TAREFAS = [
    ("ipca_luz_agua", "IBGE — IPCA da energia e da água", None),
    ("energia", "ANEEL — conta de luz", None),
    ("agua", "Cálculo — conta de água", None),
]


def main():
    estado = ler_json("estado", {}) or {}
    agora = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    falhas, ipca = 0, None

    def rodar(chave, nome, funcao):
        nonlocal falhas
        print(f"\n== {nome}")
        try:
            r = funcao()
            estado[chave] = {"nome": nome, "ok": True, "coletado_em": agora, "dado_mais_recente": r if isinstance(r, str) else None}
            print("   ok", r if isinstance(r, str) else "")
            return r
        except Exception as e:  # noqa: BLE001
            falhas += 1
            traceback.print_exc()
            ant = estado.get(chave, {})
            estado[chave] = {"nome": nome, "ok": False, "tentado_em": agora, "erro": str(e)[:300], "dado_mais_recente": ant.get("dado_mais_recente")}
            return None

    ipca = rodar("ipca_luz_agua", TAREFAS[0][1], coletar_tudo)
    rodar("energia", TAREFAS[1][1], coletar_energia)
    if ipca:
        rodar("agua", TAREFAS[2][1], lambda: coletar_agua(ipca))
    # rodar.py pode ter gravado o estado nesse meio-tempo; junta com o que está no disco
    disco = ler_json("estado", {}) or {}
    disco.update({k: estado[k] for k in ("ipca_luz_agua", "energia", "agua") if k in estado})
    salvar_json("estado", disco)
    print(f"\n{falhas} fonte(s) de luz e água com problema")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
