"""IBGE, PNAD Contínua: desemprego real e renda média de quem trabalha.

Renda média: tabela 6390 do SIDRA (rendimento médio mensal REAL, habitualmente recebido em
todos os trabalhos, pessoas ocupadas de 14 anos ou mais). Trimestre móvel, sai todo mês.

Desemprego real (definição do projeto, um número só):
    desocupados (procuram emprego) + desalentados (desistiram de procurar),
    tirando quem recebe aposentadoria ou pensão.
As tabelas prontas do IBGE não separam aposentados, então o cálculo usa os microdados
(arquivos de ~200 MB: um por trimestre e um por ano). Cada arquivo é baixado uma vez só
e o resultado fica guardado em dados/trabalho.json. Detalhes em coletar_desemprego.
"""
import io
import re
import tempfile
import time
import zipfile
from datetime import date

from comum import INICIO, SESSAO, baixar, ler_json, salvar_json

SIDRA = "https://apisidra.ibge.gov.br/values"
FTP = "https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_continua/Trimestral/Microdados"
TEMPO_MAX = 18 * 60  # segundos por coleta; o que faltar fica para a próxima

# ---------- renda média (SIDRA) ----------

def coletar_renda():
    inicio = INICIO[:4] + INICIO[5:7]
    linhas = baixar(f"{SIDRA}/t/6390/n1/all/v/5933/p/{inicio}-209912").json()[1:]
    serie = {}
    for l in linhas:
        try:
            v = float(l["V"])
        except (TypeError, ValueError):
            continue
        per = next(l[k] for k in ("D3C", "D2C", "D4C") if l.get(k, "").isdigit() and len(l[k]) == 6)
        serie[f"{per[:4]}-{per[4:6]}"] = round(v, 2)
    if not serie:
        raise RuntimeError("SIDRA 6390 veio sem valores")
    return sorted([[k, v] for k, v in serie.items()])


# ---------- desemprego real (microdados) ----------
#
# Os microdados TRIMESTRAIS não trazem a pergunta sobre aposentadoria (V5004A); ela só existe
# no arquivo ANUAL da 1ª visita. Então:
#   1. trimestre a trimestre: desocupados + desalentados (microdados trimestrais, peso V1028);
#   2. ano a ano: que fração desse grupo recebe aposentadoria ou pensão (1ª visita, peso V1032);
#   3. desemprego real = total do trimestre × (1 − fração do mesmo ano, ou do último ano já publicado).

ANUAL = FTP.replace("/Trimestral/Microdados", "/Anual/Microdados/Visita/Visita_1")


def ler_layout(texto, precisa):
    """Lê um arquivo input_*.txt (SAS) do IBGE -> {variavel: (inicio0, fim)}."""
    pos = {}
    for m in re.finditer(r"@\s*(\d+)\s+(\w+)\s+\$?\s*(\d+)\.", texto):
        ini, nome, tam = int(m.group(1)), m.group(2).upper(), int(m.group(3))
        pos[nome] = (ini - 1, ini - 1 + tam)
    faltam = [v for v in precisa if v not in pos]
    if faltam:
        raise RuntimeError(f"dicionário da PNAD sem as variáveis {faltam}")
    return pos


def somar(linhas, pos, peso, separar_aposentados=False):
    """Soma os pesos de desocupados e desalentados (e, se pedido, quantos deles são aposentados)."""
    p, oc, de = pos[peso], pos["VD4002"], pos["VD4005"]
    ap = pos["V5004A"] if separar_aposentados else None
    tot = {"desocupados": 0.0, "desalentados": 0.0, "aposentados": 0.0}
    for ln in linhas:
        if isinstance(ln, bytes):
            ln = ln.decode("latin-1")
        desoc = ln[oc[0]:oc[1]].strip() == "2"
        desal = ln[de[0]:de[1]].strip() == "1"
        if not (desoc or desal):
            continue
        w = float(ln[p[0]:p[1]].strip() or 0)
        tot["desocupados" if desoc else "desalentados"] += w
        if ap and ln[ap[0]:ap[1]].strip() == "1":
            tot["aposentados"] += w
    return tot


def listar(url, padrao):
    try:
        return sorted(set(re.findall(padrao, baixar(url, tentativas=2).text)))
    except RuntimeError:
        return []


def ler_zip_remoto(url, filtro, processar):
    with tempfile.TemporaryFile() as tmp:
        inicio = time.time()
        with SESSAO.get(url, stream=True, timeout=(20, 120)) as r:
            r.raise_for_status()
            for bloco in r.iter_content(1 << 20):
                tmp.write(bloco)
        print(f"    baixado {tmp.tell() / 1e6:.0f} MB em {time.time() - inicio:.0f}s: {url.rsplit('/', 1)[-1]}", flush=True)
        tmp.seek(0)
        z = zipfile.ZipFile(tmp)
        nome = next(n for n in z.namelist() if filtro(n.lower()))
        with z.open(nome) as f:
            return processar(f)


def layout_trimestral():
    nomes = listar(f"{FTP}/Documentacao/", r'href="(Dicionario_e_input[^"]+\.zip)"')
    if not nomes:
        raise RuntimeError("não achei o dicionário da PNAD trimestral")
    z = zipfile.ZipFile(io.BytesIO(baixar(f"{FTP}/Documentacao/{nomes[-1]}").content))
    nome = next(n for n in z.namelist() if n.lower().startswith("input") and n.lower().endswith(".txt"))
    return ler_layout(z.read(nome).decode("latin-1"), ["V1028", "VD4002", "VD4005"])


def trimestres_disponiveis():
    """{'2026-T2': ('2026/PNADC_022026.zip', 'PNADC_022026.zip')} a partir do ano de início."""
    achados = {}
    for ano in range(int(INICIO[:4]), date.today().year + 1):
        for arq, tri, a in listar(f"{FTP}/{ano}/", r'href="(PNADC_(\d{2})(\d{4})[^"]*\.zip)"'):
            achados[f"{a}-T{int(tri)}"] = (f"{ano}/{arq}", arq)
    return achados


def anos_disponiveis():
    """{'2025': ('PNADC_2025_visita1_....zip', 'input_PNADC_2025_visita1_....txt')}"""
    dados = {a: arq for arq, a in listar(f"{ANUAL}/Dados/", r'href="(PNADC_(\d{4})_visita1[^"]*\.zip)"')}
    docs = {a: arq for arq, a in listar(f"{ANUAL}/Documentacao/", r'href="(input_PNADC_(\d{4})_visita1[^"]*\.txt)"')}
    return {a: (dados[a], docs[a]) for a in dados if a in docs and a >= INICIO[:4]}


def faltando(feitos, disponiveis, chave):
    return [k for k in sorted(disponiveis) if feitos.get(k, {}).get("arquivo") != disponiveis[k][0 if chave == "ano" else 1]]


def coletar_desemprego(anterior, inicio_coleta):
    anos = {a["ano"]: a for a in anterior.get("desemprego_aposentados_por_ano", [])}
    tris = {t["trimestre"]: t for t in anterior.get("desemprego_trimestres", [])}
    tempo = lambda: time.time() - inicio_coleta > TEMPO_MAX  # noqa: E731
    pendentes = 0

    # 1) fração de aposentados por ano (arquivo anual da 1ª visita)
    disp_anos = anos_disponiveis()
    for ano in faltando(anos, disp_anos, "ano"):
        if tempo():
            pendentes += 1
            continue
        dado, entrada = disp_anos[ano]
        pos = ler_layout(baixar(f"{ANUAL}/Documentacao/{entrada}").content.decode("latin-1"),
                         ["V1032", "VD4002", "VD4005", "V5004A"])
        t = ler_zip_remoto(f"{ANUAL}/Dados/{dado}", lambda n: n.endswith(".txt"),
                           lambda f: somar(f, pos, "V1032", separar_aposentados=True))
        grupo = t["desocupados"] + t["desalentados"]
        anos[ano] = {"ano": ano, "arquivo": dado, "fracao_aposentados": round(t["aposentados"] / grupo, 5)}
        print(f"  {ano}: {anos[ano]['fracao_aposentados'] * 100:.1f}% dos sem trabalho recebem aposentadoria ou pensão", flush=True)

    # 2) desocupados + desalentados por trimestre
    disp_tris = trimestres_disponiveis()
    pend_tris = faltando(tris, disp_tris, "tri")
    pos = layout_trimestral() if pend_tris else None
    for tri in pend_tris:
        if tempo():
            pendentes += 1
            continue
        caminho, arq = disp_tris[tri]
        t = ler_zip_remoto(f"{FTP}/{caminho}", lambda n: n.endswith(".txt"), lambda f: somar(f, pos, "V1028"))
        tris[tri] = {"trimestre": tri, "arquivo": arq,
                     "desocupados": round(t["desocupados"]), "desalentados": round(t["desalentados"])}
        print(f"  {tri}: {(t['desocupados'] + t['desalentados']) / 1e6:.2f} milhões sem trabalho (antes de tirar aposentados)", flush=True)
    if pendentes:
        print(f"  tempo esgotado; {pendentes} arquivo(s) ficam para a próxima coleta")

    # 3) junta
    for t in tris.values():
        usados = [a for a in sorted(anos) if a <= t["trimestre"][:4]] or sorted(anos)[:1]
        if not usados:
            t.pop("total", None)
            continue
        f = anos[usados[-1]]["fracao_aposentados"]
        t["fracao_aposentados_ano"] = usados[-1]
        t["total"] = round((t["desocupados"] + t["desalentados"]) * (1 - f))
    return [anos[a] for a in sorted(anos)], [tris[t] for t in sorted(tris)], pendentes


def coletar():
    inicio = time.time()
    anterior = ler_json("trabalho", {}) or {}
    dados = {
        "fonte": "IBGE — PNAD Contínua",
        "fonte_url": "https://sidra.ibge.gov.br/tabela/6390",
        "renda_media": anterior.get("renda_media", []),
        "desemprego_trimestres": anterior.get("desemprego_trimestres", []),
        "desemprego_aposentados_por_ano": anterior.get("desemprego_aposentados_por_ano", []),
    }
    erros = []
    try:
        dados["renda_media"] = coletar_renda()
    except Exception as e:  # noqa: BLE001
        erros.append(f"renda: {e}")
    try:
        (dados["desemprego_aposentados_por_ano"], dados["desemprego_trimestres"],
         faltam) = coletar_desemprego(dados, inicio)
        dados["desemprego_faltam"] = faltam
    except Exception as e:  # noqa: BLE001
        erros.append(f"desemprego: {e}")
    dados["desemprego_real"] = [[t["trimestre"], t["total"]] for t in dados["desemprego_trimestres"] if "total" in t]
    salvar_json("trabalho", dados)  # guarda o que deu certo antes de avisar do erro
    if erros:
        raise RuntimeError("; ".join(erros))
    ult = [s[-1][0] for s in (dados["renda_media"], dados["desemprego_real"]) if s]
    return " / ".join(ult) or None


if __name__ == "__main__":
    print(coletar())
