"""Diagnóstico das fontes: grava em descobertas/ o que cada site oferece hoje.

Serve para ajustar os coletores quando uma fonte muda de formato. Não altera dados/.
"""
import json
import re

from comum import DESCOBERTAS, baixar, norm

SIDRA_TABELAS = [7060, 6318, 6807, 4093, 4099, 4092, 5436, 6390, 6387, 6785, 6800, 6461, 4097, 4094]
PAGINAS = {
    "anp_serie": "https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/precos/precos-revenda-e-de-distribuicao-combustiveis/serie-historica-do-levantamento-de-precos",
    "anp_semanas": "https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/precos/levantamento-de-precos-de-combustiveis-ultimas-semanas-pesquisadas",
    "anp_dados_abertos": "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/serie-historica-de-precos-de-combustiveis",
    "dieese_cesta": "https://www.dieese.org.br/cesta/",
    "dieese_salario": "https://www.dieese.org.br/analisecestabasica/salarioMinimo.html",
}


def guardar(nome, texto):
    DESCOBERTAS.mkdir(exist_ok=True)
    (DESCOBERTAS / nome).write_text(texto, encoding="utf-8")


def main():
    resumo = []
    for nome, url in PAGINAS.items():
        try:
            r = baixar(url)
            html = r.text
            links = sorted(set(re.findall(r'(?:href|action|src)="([^"]+)"', html)))
            guardar(f"{nome}_links.txt", "\n".join(links))
            if nome.startswith("dieese"):
                guardar(f"{nome}.html", html)
                forms = re.findall(r"<form.*?</form>", html, re.S | re.I)
                scripts = re.findall(r"<script[^>]*>(.*?)</script>", html, re.S | re.I)
                guardar(f"{nome}_forms.txt", "\n\n----\n\n".join(forms) + "\n\n==== SCRIPTS ====\n\n" + "\n\n----\n\n".join(s[:4000] for s in scripts))
            resumo.append(f"OK   {nome}: {len(html)} bytes, {len(links)} links")
        except Exception as e:  # noqa: BLE001
            resumo.append(f"ERRO {nome}: {e}")

    for t in SIDRA_TABELAS:
        try:
            meta = baixar(f"https://servicodados.ibge.gov.br/api/v3/agregados/{t}/metadados").json()
            linhas = [f"TABELA {t}: {meta.get('nome')}", f"periodicidade: {meta.get('periodicidade')}",
                      f"niveis: {meta.get('nivelTerritorial')}", "VARIAVEIS:"]
            linhas += [f"  {v['id']}: {v['nome']} ({v.get('unidade')})" for v in meta.get("variaveis", [])]
            for c in meta.get("classificacoes", []):
                linhas.append(f"CLASSIFICACAO {c['id']}: {c['nome']}")
                linhas += [f"  {k['id']}: {k['nome']}" for k in c.get("categorias", [])]
            guardar(f"sidra_{t}.txt", "\n".join(linhas))
            resumo.append(f"OK   sidra {t}: {meta.get('nome')}")
        except Exception as e:  # noqa: BLE001
            resumo.append(f"ERRO sidra {t}: {e}")

    try:
        pesquisas = baixar("https://servicodados.ibge.gov.br/api/v3/agregados").json()
        linhas = []
        for p in pesquisas:
            if any(k in norm(p.get("nome")) for k in ("pnad continua", "indice nacional de precos")):
                for a in p.get("agregados", []):
                    linhas.append(f"{a['id']}\t{p['nome']}\t{a['nome']}")
        guardar("sidra_tabelas_pnad_ipca.txt", "\n".join(linhas))
        resumo.append(f"OK   lista de tabelas SIDRA: {len(linhas)}")
    except Exception as e:  # noqa: BLE001
        resumo.append(f"ERRO lista SIDRA: {e}")

    guardar("RESUMO.txt", "\n".join(resumo))
    print("\n".join(resumo))


if __name__ == "__main__":
    main()
