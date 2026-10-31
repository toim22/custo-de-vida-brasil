"""Roda todos os coletores. Uma fonte com problema não impede as outras.

Grava dados/estado.json com a data e o resultado de cada coleta. Sai com código 1 se
alguma fonte falhar, para o GitHub avisar por e-mail (o site continua com o último dado bom).
"""
import sys
import traceback
from datetime import datetime, timezone

import anp
import calculos
import dieese
import ibge
from comum import ler_json, salvar_json

TAREFAS = [
    ("combustiveis", "ANP — combustíveis e gás", anp.coletar),
    ("salario", "DIEESE — salário mínimo", dieese.coletar_salario),
    ("cesta", "DIEESE — cesta básica", dieese.coletar_cesta),
    ("ipca", "IBGE — IPCA", ibge.coletar),
    ("churrasco", "Cálculo — itens avulsos e Churrasco pra 6", calculos.calcular),
]


def main():
    estado = ler_json("estado", {}) or {}
    falhas = 0
    agora = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    for chave, nome, funcao in TAREFAS:
        print(f"\n== {nome}")
        try:
            ultimo = funcao()
            estado[chave] = {"nome": nome, "ok": True, "coletado_em": agora, "dado_mais_recente": ultimo}
            print(f"   ok, dado mais recente: {ultimo}")
        except Exception as e:  # noqa: BLE001
            falhas += 1
            traceback.print_exc()
            anterior = estado.get(chave, {})
            estado[chave] = {"nome": nome, "ok": False, "tentado_em": agora, "erro": str(e)[:300],
                             "dado_mais_recente": anterior.get("dado_mais_recente")}
    salvar_json("estado", estado)
    print(f"\n{falhas} fonte(s) com problema")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
