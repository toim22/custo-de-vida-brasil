"""Radar de impostos: procura, 2x ao dia, projetos novos e notícias sobre aumento de imposto.

Fontes:
- Câmara dos Deputados (API de dados abertos): PL, PLP, PEC e MPV apresentados nos últimos dias.
- Senado Federal (API de dados abertos): idem.
- Google Notícias (RSS), só de veículos da lista em config/impostos_radar.json.

O resultado vai para dados/impostos-radar.json e aparece na página de aumentos de impostos
numa seção separada, marcada como "achado automático, ainda não conferido". Os cartões principais
(dados/aumentos-impostos.json) continuam sendo conferidos à mão: o robô não mexe neles.

Se uma fonte falhar, fica o que já estava salvo dela.
"""
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

from comum import baixar, config, ler_json, norm, salvar_json

HOJE = datetime.now(timezone(timedelta(hours=-3))).date()
JSON = {"Accept": "application/json"}

# Ementa fala de imposto/tributo...
RE_TRIBUTO = re.compile(
    r"\b(imposto|tribut|contribuicao social|contribuicao de intervencao|aliquota|taxa de fiscalizacao|grandes fortunas|"
    r"(cide|cbs|ibs|ipi|iof|icms|iss|issqn|ipva|iptu|itcmd|irpf|irpj|irrf|csll|cofins|pis)\b)")
# ...e sugere criar, aumentar ou estender a cobrança.
RE_SOBE = re.compile(
    r"\b(institui|cria|criar|instituir|eleva|elevar|aumenta|aumentar|majora|majorar|amplia|ampliar|incidencia|"
    r"passa a incidir|tributacao|tributar|taxar|altera a aliquota|alterar a aliquota|novas aliquotas)")
# Fim de isenção é aumento, mesmo tendo a palavra "isenção".
RE_FIM_ISENCAO = re.compile(r"\b(revoga\w*|extingu\w*|fim d\w*|elimina\w*|acaba\w*)\b.{0,40}\b(isenc|beneficio|reducao)")
# O que é redução, isenção ou só destino do dinheiro fica de fora.
RE_DESCE = re.compile(
    r"\b(isenc|isent|reduz|reducao|reduzir|exclui|excluir|nao incidencia|devolucao|cashback|deducao|deduzir|zera|zerar|"
    r"imunidade|parcelamento|refis|destinacao|reparticao|transferencia|credito presumido|diferimento|suspensao|"
    r"desonera|beneficio fiscal|incentivo|anistia|remissao|prorroga|restitui)")

RE_NOTICIA_SOBE = re.compile(
    r"\b(novo imposto|aumento d\w* imposto|aumenta\w* (o |a )?(imposto|aliquota|tribut)|eleva\w* (o |a )?(imposto|aliquota)|"
    r"taxa\w*|taxacao|tributa\w*|aliquota\w* sobe|sobe (o |a )?(imposto|aliquota)|mais imposto|imposto sobre|"
    r"cria\w* (o |um |novo )?(imposto|tributo|taxa)|fim da isencao|acaba com isencao)")
RE_NOTICIA_TRIBUTO = re.compile(r"\b(imposto|tribut|aliquota|taxa|taxar|taxacao|cbs|ibs|iof|ipi|icms|ir |dividendo|fortuna)")
RE_NOTICIA_DESCE = re.compile(r"\b(reduz|reducao|isencao do ir|isento|zera|corta imposto|cashback|devolucao|restituicao)")


def parece_aumento(ementa):
    e = norm(ementa)
    if not RE_TRIBUTO.search(e):
        return False
    if RE_FIM_ISENCAO.search(e):
        return True
    return bool(RE_SOBE.search(e)) and not RE_DESCE.search(e)


def numero_fmt(sigla, numero, ano):
    n = int(numero)
    return f"{sigla} {n:,}/{ano}".replace(",", ".")


def chave_instrumento(txt):
    """'PL 5.889/2026' -> 'pl 5889/2026' (para achar o que já está nos cartões)."""
    return {f"{s.lower()} {n.replace('.', '')}/{a}" for s, n, a in re.findall(r"\b(PLP|PLV|PEC|PL|MPV|MP)\s*([\d.]+)/(\d{4})", txt or "", re.I)}


# ---------------- Câmara ----------------

def camara(inicio, fim):
    base = "https://dadosabertos.camara.leg.br/api/v2"
    achados, pagina = [], 1
    while pagina <= 30:
        url = (f"{base}/proposicoes?dataApresentacaoInicio={inicio}&dataApresentacaoFim={fim}"
               f"&siglaTipo=PL,PLP,PEC,MPV&itens=100&pagina={pagina}&ordem=ASC&ordenarPor=id")
        dados = baixar(url, headers=JSON).json().get("dados", [])
        for p in dados:
            if parece_aumento(p.get("ementa")):
                achados.append(p)
        if len(dados) < 100:
            break
        pagina += 1
    saida = []
    for p in achados[:60]:
        autor = ""
        try:
            autores = baixar(f"{base}/proposicoes/{p['id']}/autores", headers=JSON, tentativas=2).json().get("dados", [])
            if autores:
                a = autores[0]
                autor = a.get("nome", "")
                m = re.search(r"/deputados/(\d+)", a.get("uri") or "")
                if m:
                    dep = baixar(f"{base}/deputados/{m.group(1)}", headers=JSON, tentativas=2).json()["dados"]["ultimoStatus"]
                    autor = f"{dep.get('nomeEleitoral') or autor} ({dep.get('siglaPartido')}-{dep.get('siglaUf')})"
                if len(autores) > 1:
                    autor += f" e mais {len(autores) - 1}"
        except Exception as e:  # noqa: BLE001
            print(f"    autor de {p['id']} não saiu: {e}")
        saida.append({
            "id": f"camara-{p['id']}",
            "casa": "Câmara",
            "numero": numero_fmt(p["siglaTipo"], p["numero"], p["ano"]),
            "data": (p.get("dataApresentacao") or "")[:10],
            "ementa": p.get("ementa", "").strip(),
            "autor": autor,
            "link": f"https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={p['id']}",
        })
    return saida


# ---------------- Senado ----------------

def senado(inicio, fim):
    url = ("https://legis.senado.leg.br/dadosabertos/materia/pesquisa/lista.json"
           f"?dataInicioApresentacao={inicio.replace('-', '')}&dataFimApresentacao={fim.replace('-', '')}")
    mats = (baixar(url, headers=JSON).json().get("PesquisaBasicaMateria", {}).get("Materias") or {}).get("Materia") or []
    if isinstance(mats, dict):
        mats = [mats]
    saida = []
    for m in mats:
        if m.get("Sigla") not in ("PL", "PLP", "PEC", "MPV") or not parece_aumento(m.get("Ementa")):
            continue
        saida.append({
            "id": f"senado-{m['Codigo']}",
            "casa": "Senado",
            "numero": numero_fmt(m["Sigla"], m["Numero"], m["Ano"]),
            "data": m.get("Data", "")[:10],
            "ementa": (m.get("Ementa") or "").strip(),
            "autor": m.get("Autor", ""),
            "link": f"https://www25.senado.leg.br/web/atividade/materias/-/materia/{m['Codigo']}",
        })
    return saida


# ---------------- Notícias ----------------

def noticias(cfg):
    confiaveis = {norm(f) for f in cfg["fontes_confiaveis"]}
    dias = cfg.get("dias_noticias", 4)
    saida = []
    for q in cfg["buscas_noticias"]:
        url = f"https://news.google.com/rss/search?q={quote_plus(q + f' when:{dias}d')}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
        try:
            raiz = ET.fromstring(baixar(url, tentativas=2).content)
        except Exception as e:  # noqa: BLE001
            print(f"    busca '{q}' falhou: {e}")
            continue
        for it in raiz.iter("item"):
            fonte_el = it.find("source")
            fonte = (fonte_el.text or "").strip() if fonte_el is not None else ""
            titulo = (it.findtext("title") or "").strip()
            if fonte and titulo.endswith(" - " + fonte):
                titulo = titulo[: -len(fonte) - 3].strip()
            if norm(fonte) not in confiaveis:
                continue
            t = norm(titulo)
            if not (RE_NOTICIA_TRIBUTO.search(t) and RE_NOTICIA_SOBE.search(t)) or RE_NOTICIA_DESCE.search(t):
                continue
            try:
                quando = parsedate_to_datetime(it.findtext("pubDate")).astimezone(timezone(timedelta(hours=-3)))
            except Exception:  # noqa: BLE001
                continue
            saida.append({
                "id": "n-" + re.sub(r"[^a-z0-9]+", "-", t)[:80],
                "titulo": titulo,
                "fonte": fonte,
                "data": quando.date().isoformat(),
                "hora": quando.strftime("%H:%M"),
                "link": (it.findtext("link") or "").strip(),
            })
    return saida


def parecido(a, b):
    """Duas manchetes quase iguais (mesma notícia em veículos diferentes)."""
    pa, pb = set(norm(a).split()), set(norm(b).split())
    return len(pa & pb) / max(1, min(len(pa), len(pb))) >= 0.75


def main():
    cfg = config("impostos_radar")
    antigo = ler_json("impostos-radar", {}) or {}
    curados = ler_json("aumentos-impostos", {}) or {}
    ja_listados = set()
    for i in curados.get("itens", []):
        ja_listados |= chave_instrumento(i.get("instrumento"))

    inicio = (HOJE - timedelta(days=cfg.get("dias_projetos", 15))).isoformat()
    fim = HOJE.isoformat()
    falhas = []

    projetos_novos = []
    for nome, func in (("Câmara", camara), ("Senado", senado)):
        print(f"  {nome}: projetos de {inicio} a {fim}")
        try:
            achou = func(inicio, fim)
            print(f"    {len(achou)} com cara de aumento de imposto")
            projetos_novos += achou
        except Exception as e:  # noqa: BLE001
            print(f"    {nome} falhou: {e}")
            falhas.append(nome)
            projetos_novos += [p for p in antigo.get("projetos", []) if p.get("casa") == nome]

    print("  Notícias (Google Notícias, veículos da lista)")
    try:
        nots = noticias(cfg)
    except Exception as e:  # noqa: BLE001
        print(f"    notícias falharam: {e}")
        falhas.append("Notícias")
        nots = []

    # junta com o que já estava salvo, sem repetir, e guarda a data em que o robô viu pela primeira vez
    visto = {p["id"]: p.get("visto_em", fim) for p in antigo.get("projetos", []) + antigo.get("noticias", [])}
    limite_p = (HOJE - timedelta(days=cfg.get("guardar_projetos_dias", 60))).isoformat()
    projetos = {p["id"]: p for p in antigo.get("projetos", []) if p.get("data", "") >= limite_p}
    for p in projetos_novos:
        projetos[p["id"]] = p
    for p in projetos.values():
        p["visto_em"] = visto.get(p["id"], fim)
        p["ja_nos_cartoes"] = bool(chave_instrumento(p["numero"]) & ja_listados)

    limite_n = (HOJE - timedelta(days=cfg.get("guardar_noticias_dias", 10))).isoformat()
    lista_n = [n for n in antigo.get("noticias", []) if n.get("data", "") >= limite_n] + nots
    lista_n.sort(key=lambda n: (n["data"], n.get("hora", "")), reverse=True)
    unicas = []
    for n in lista_n:
        if any(n["id"] == u["id"] or n["link"] == u["link"] or parecido(n["titulo"], u["titulo"]) for u in unicas):
            continue
        n["visto_em"] = visto.get(n["id"], fim)
        unicas.append(n)

    salvar_json("impostos-radar", {
        "atualizado": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "nota": "Achados automáticos, ainda não conferidos. Projetos vêm das APIs da Câmara e do Senado (filtro pelo resumo oficial). "
                "Notícias vêm do Google Notícias, só de veículos conhecidos. Um item só vira cartão depois de conferido.",
        "falhas": falhas,
        "projetos": sorted(projetos.values(), key=lambda p: (p["data"], p["id"]), reverse=True),
        "noticias": unicas[: cfg.get("max_noticias", 15)],
    })
    print(f"  radar salvo: {len(projetos)} projetos, {len(unicas[: cfg.get('max_noticias', 15)])} notícias; falhas: {falhas or 'nenhuma'}")
    return 1 if len(falhas) == 3 else 0


if __name__ == "__main__":
    sys.exit(main())
