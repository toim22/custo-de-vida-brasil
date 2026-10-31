# Custo de Vida Brasil

Site que acompanha quanto custa viver no Brasil: cesta básica item a item, combustíveis e gás toda semana, Churrasco pra 6, salário mínimo e o que ele compra. Dados desde janeiro de 2023, por Brasil, região e estado.

Nome provisório. O site é estático (HTML, CSS e JavaScript, sem servidor) e fica hospedado de graça no GitHub Pages.

## Como funciona

- `coletores/` — robôs em Python que baixam os dados das fontes oficiais (ANP, DIEESE, IBGE).
- `dados/` — os dados coletados, em JSON. Públicos: qualquer pessoa pode baixar.
- `config/` — o que é editado à mão: itens avulsos e Churrasco pra 6 (`itens.json`), regras de impostos (`impostos.json`) e carro zero mais barato (`carro.json`).
- `descobertas/` — diagnóstico das fontes, gravado a cada coleta, para ajustar os robôs quando um site muda.
- `.github/workflows/site.yml` — roda a coleta toda segunda às 9h (Brasília) e todo dia 15, grava os dados e publica o site.

## Tarefas manuais

- **Carro zero mais barato (1× por mês):** acrescente uma linha em `config/carro.json`.
- **Impostos (quando a lei muda):** acrescente um período em `config/impostos.json`.
- **Preços de referência dos itens avulsos (a cada 6 meses):** atualize `config/itens.json`.

Dá para editar esses arquivos direto no site do GitHub (ícone de lápis). O site se atualiza sozinho em alguns minutos.

## Rodar a coleta na mão

Na aba **Actions**, escolha "Coletar dados e publicar o site" e clique em **Run workflow**.

## Como calculamos

Ver `como-calculamos.html` (também no rodapé do site).
