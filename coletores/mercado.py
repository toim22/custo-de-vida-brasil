"""Dólar, Ibovespa e ações das estatais, pelo Yahoo Finance (gratuito, sem chave).

Grava dois arquivos:
- dados/mercado.json: fechamento de cada dia desde 2023 + preços de 15 em 15 minutos dos últimos 5 pregões
  (usado na página mercado.html);
- dados/mercado-agora.json: só o último preço de cada ativo (pequeno, carregado no topo de todas as páginas).

Roda 2x por dia junto com as outras fontes (e o resultado vai para o repositório) e, nos dias úteis,
de hora em hora durante o pregão, só para publicar o site com o preço mais novo (sem gravar no repositório).
Os preços da B3 no Yahoo têm atraso de cerca de 15 minutos.
"""
import sys
import time
from datetime import datetime, timedelta, timezone

import json

from comum import DADOS, INICIO, baixar, config, ler_json, salvar_json

BRT = timezone(timedelta(hours=-3))
URL = "https://query1.finance.yahoo.com/v8/finance/chart/{s}?{q}"
URL2 = "https://query2.finance.yahoo.com/v8/finance/chart/{s}?{q}"


def grafico(simbolo, q):
    s = simbolo.replace("^", "%5E").replace("=", "%3D")
    erro = None
    for base in (URL, URL2):
        try:
            j = baixar(base.format(s=s, q=q), tentativas=2, timeout=(10, 30)).json()
            res = j["chart"]["result"][0]
            return res
        except Exception as e:  # noqa: BLE001
            erro = e
    raise RuntimeError(f"{simbolo}: {erro}")


def pontos(res, fmt, fuso=BRT, casas=2):
    ts = res.get("timestamp") or []
    fech = ((res.get("indicators") or {}).get("quote") or [{}])[0].get("close") or []
    out = {}
    for t, c in zip(ts, fech):
        if c is None:
            continue
        out[datetime.fromtimestamp(t, fuso).strftime(fmt)] = round(float(c), casas)
    return out


def um_ativo(a, antigo):
    inicio = int(datetime.fromisoformat(INICIO).replace(tzinfo=BRT).timestamp())
    agora = int(time.time())
    diario_res = grafico(a["yahoo"], f"period1={inicio}&period2={agora}&interval=1d")
    meta = diario_res.get("meta") or {}
    # o dia de cada fechamento segue o fuso da bolsa (o dólar fecha à meia-noite de Londres)
    fuso = timezone(timedelta(seconds=meta.get("gmtoffset") or 0)) if a["tipo"] == "moeda" else BRT
    casas = 4 if a["tipo"] == "moeda" else 2
    diario = pontos(diario_res, "%Y-%m-%d", fuso, casas)
    intradia_res = grafico(a["yahoo"], "range=5d&interval=15m")
    intradia = pontos(intradia_res, "%Y-%m-%dT%H:%M", BRT, casas)
    meta_i = intradia_res.get("meta") or {}
    # mantém o histórico já coletado (se o Yahoo devolver menos dias desta vez)
    junto = dict((antigo or {}).get("diario") or [])
    junto.update(diario)
    preco = meta_i.get("regularMarketPrice") or meta.get("regularMarketPrice")
    hora = meta_i.get("regularMarketTime") or meta.get("regularMarketTime")
    dia_preco = datetime.fromtimestamp(hora, fuso).strftime("%Y-%m-%d") if hora else None
    if preco and dia_preco:
        junto[dia_preco] = round(float(preco), casas)
    dias = sorted(junto)
    # fechamento anterior = último dia antes do dia do preço atual
    ant = [d for d in dias if dia_preco and d < dia_preco]
    anterior = junto[ant[-1]] if ant else None
    return {
        "nome": a["nome"],
        "descricao": a.get("descricao"),
        "tipo": a["tipo"],
        "controle": a.get("controle"),
        "esfera": a.get("esfera"),
        "preco": round(float(preco), casas) if preco else (junto[dias[-1]] if dias else None),
        "anterior": anterior,
        "hora": datetime.fromtimestamp(hora, BRT).strftime("%Y-%m-%dT%H:%M") if hora else None,
        "diario": [[d, junto[d]] for d in dias],
        "intradia": sorted([k, v] for k, v in intradia.items()),
    }


def coletar():
    cfg = config("mercado")
    antigo = ler_json("mercado", {}) or {}
    ativos, falhas = {}, []
    for a in cfg["ativos"]:
        try:
            ativos[a["id"]] = um_ativo(a, (antigo.get("ativos") or {}).get(a["id"]))
            x = ativos[a["id"]]
            print(f"   {a['id']}: {x['preco']} em {x['hora']} ({len(x['diario'])} dias, {len(x['intradia'])} pontos no dia)")
        except Exception as e:  # noqa: BLE001
            falhas.append(f"{a['id']}: {e}")
            print(f"   {a['id']} falhou: {e}")
            if (antigo.get("ativos") or {}).get(a["id"]):
                ativos[a["id"]] = antigo["ativos"][a["id"]]
    if not ativos or len(falhas) == len(cfg["ativos"]):
        raise RuntimeError("nenhum ativo coletado: " + "; ".join(falhas)[:250])
    agora = datetime.now(BRT).strftime("%Y-%m-%dT%H:%M")
    ordem = [a["id"] for a in cfg["ativos"] if a["id"] in ativos]
    # sem espaços: o arquivo tem quase 10 mil números
    DADOS.mkdir(exist_ok=True)
    (DADOS / "mercado.json").write_text(json.dumps({
        "atualizado": agora,
        "fonte": "Yahoo Finance (cotações da B3 com cerca de 15 minutos de atraso)",
        "fonte_url": "https://finance.yahoo.com/quote/%5EBVSP/",
        "ordem": ordem,
        "ex_estatais": cfg.get("ex_estatais", []),
        "ativos": ativos,
    }, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    salvar_json("mercado-agora", {
        "atualizado": agora,
        "ativos": {k: {"nome": ativos[k]["nome"], "preco": ativos[k]["preco"], "anterior": ativos[k]["anterior"],
                       "hora": ativos[k]["hora"]} for k in ("USD", "IBOV") if k in ativos},
    })
    if falhas:
        print("   com falha: " + "; ".join(falhas))
    return agora


if __name__ == "__main__":
    try:
        coletar()
    except Exception as e:  # noqa: BLE001
        print(f"mercado falhou: {e}")
        sys.exit(1)
