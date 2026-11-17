"""IBGE, PNAD Contínua: desemprego real e renda média de quem trabalha.

Renda média: tabela 6390 do SIDRA (rendimento médio mensal REAL, habitualmente recebido em
todos os trabalhos, pessoas ocupadas de 14 anos ou mais). Trimestre móvel, sai todo mês.

Desemprego real (definição do projeto, um número só):
    desocupados (procuram emprego) + desalentados (desistiram de procurar),
    tirando quem recebe aposentadoria ou pensão.
As tabelas prontas do IBGE não separam aposentados, então o cálculo usa os microdados
trimestrais (arquivos de ~220 MB, um por trimestre). Cada trimestre é baixado uma vez só
e o resultado fica guardado em dados/trabalho.json.
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

# Variáveis dos microdados (dicionário do IBGE)
VARS = {
    "V1028": "peso do morador no trimestre",
    "VD4002": "condição de ocupação (1 ocupado, 2 desocupado)",
    "VD4005": "desalentado (1 sim)",
    "V5004A": "recebia aposentadoria ou pensão de instituto de previdência (1 sim)",
}


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

def ler_layout(texto):
    """Lê o arquivo input_PNADC_trimestral.txt (SAS) -> {variavel: (inicio0, fim)}."""
    pos = {}
    for m in re.finditer(r"@\s*(\d+)\s+(\w+)\s+\$?\s*(\d+)\.", texto):
        ini, nome, tam = int(m.group(1)), m.group(2).upper(), int(m.group(3))
        pos[nome] = (ini - 1, ini - 1 + tam)
    faltam = [v for v in VARS if v not in pos]
    if faltam:
        raise RuntimeError(f"dicionário da PNAD sem as variáveis {faltam}")
    return pos


def somar(linhas, pos):
    """Soma os pesos. Devolve contagens em número de pessoas."""
    p, oc, de, ap = (pos[v] for v in ("V1028", "VD4002", "VD4005", "V5004A"))
    tot = {"desocupados": 0.0, "desalentados": 0.0, "aposentados_tirados": 0.0}
    for ln in linhas:
        if isinstance(ln, bytes):
            ln = ln.decode("latin-1")
        desoc = ln[oc[0]:oc[1]].strip() == "2"
        desal = ln[de[0]:de[1]].strip() == "1"
        if not (desoc or desal):
            continue
        peso = float(ln[p[0]:p[1]].strip() or 0)
        if ln[ap[0]:ap[1]].strip() == "1":
            tot["aposentados_tirados"] += peso
            continue
        tot["desocupados" if desoc else "desalentados"] += peso
    return tot


def layout_atual():
    r = baixar(f"{FTP}/Documentacao/")
    nomes = sorted(set(re.findall(r'href="(Dicionario_e_input[^"]+\.zip)"', r.text)))
    if not nomes:
        raise RuntimeError("não achei o dicionário da PNAD em Documentacao/")
    z = zipfile.ZipFile(io.BytesIO(baixar(f"{FTP}/Documentacao/{nomes[-1]}").content))
    nome = next(n for n in z.namelist() if n.lower().startswith("input") and n.lower().endswith(".txt"))
    return ler_layout(z.read(nome).decode("latin-1"))


def arquivos_disponiveis():
    """{'2026-T2': ('2026/PNADC_022026.zip', 'PNADC_022026.zip')} a partir do ano de início."""
    achados = {}
    for ano in range(int(INICIO[:4]), date.today().year + 1):
        try:
            r = baixar(f"{FTP}/{ano}/", tentativas=2)
        except RuntimeError:
            continue  # ano ainda sem pasta
        for nome in sorted(set(re.findall(r'href="(PNADC_(\d{2})(\d{4})[^"]*\.zip)"', r.text))):
            arq, tri, a = nome
            achados[f"{a}-T{int(tri)}"] = (f"{ano}/{arq}", arq)
    return achados


def processar_trimestre(caminho, pos):
    with tempfile.TemporaryFile() as tmp:
        inicio = time.time()
        with SESSAO.get(f"{FTP}/{caminho}", stream=True, timeout=(20, 120)) as r:
            r.raise_for_status()
            for bloco in r.iter_content(1 << 20):
                tmp.write(bloco)
        print(f"    baixado {tmp.tell() / 1e6:.0f} MB em {time.time() - inicio:.0f}s: {caminho}", flush=True)
        tmp.seek(0)
        z = zipfile.ZipFile(tmp)
        nome = next(n for n in z.namelist() if n.lower().endswith(".txt"))
        with z.open(nome) as f:
            return somar(f, pos)


def coletar_desemprego(guardado, inicio_coleta):
    feitos = {t["trimestre"]: t for t in guardado}
    disponiveis = arquivos_disponiveis()
    pendentes = [t for t in sorted(disponiveis) if feitos.get(t, {}).get("arquivo") != disponiveis[t][1]]
    if not pendentes:
        return guardado, 0
    pos = layout_atual()
    for tri in pendentes:
        if time.time() - inicio_coleta > TEMPO_MAX:
            print(f"  tempo esgotado; faltam {len(pendentes)} trimestre(s) para a próxima coleta")
            break
        caminho, arq = disponiveis[tri]
        tot = processar_trimestre(caminho, pos)
        feitos[tri] = {"trimestre": tri, "arquivo": arq,
                       "desocupados": round(tot["desocupados"]), "desalentados": round(tot["desalentados"]),
                       "aposentados_tirados": round(tot["aposentados_tirados"]),
                       "total": round(tot["desocupados"] + tot["desalentados"])}
        print(f"  {tri}: desemprego real {feitos[tri]['total'] / 1e6:.2f} milhões", flush=True)
        pendentes = pendentes[1:]
    return [feitos[t] for t in sorted(feitos)], len(pendentes)


def coletar():
    inicio = time.time()
    anterior = ler_json("trabalho", {}) or {}
    dados = {
        "fonte": "IBGE — PNAD Contínua",
        "fonte_url": "https://sidra.ibge.gov.br/tabela/6390",
        "renda_media": anterior.get("renda_media", []),
        "desemprego_trimestres": anterior.get("desemprego_trimestres", []),
    }
    erros = []
    try:
        dados["renda_media"] = coletar_renda()
    except Exception as e:  # noqa: BLE001
        erros.append(f"renda: {e}")
    try:
        dados["desemprego_trimestres"], faltam = coletar_desemprego(dados["desemprego_trimestres"], inicio)
        dados["desemprego_faltam"] = faltam
    except Exception as e:  # noqa: BLE001
        erros.append(f"desemprego: {e}")
    dados["desemprego_real"] = [[t["trimestre"], t["total"]] for t in dados["desemprego_trimestres"]]
    salvar_json("trabalho", dados)  # guarda o que deu certo antes de avisar do erro
    if erros:
        raise RuntimeError("; ".join(erros))
    ult = [s[-1][0] for s in (dados["renda_media"], dados["desemprego_real"]) if s]
    return " / ".join(ult) or None


if __name__ == "__main__":
    print(coletar())
