/* Funções comuns a todas as páginas. Sem dependências externas. */
(function () {
  "use strict";

  var SITE = {
    nome: "Tudo Caro",
    // Endereço do GoatCounter (ex.: "https://custodevida.goatcounter.com"). Vazio = contador desligado.
    contador: ""
  };

  var MENU = [
    ["index.html", "Início"],
    ["cesta.html", "Cesta básica"],
    ["combustiveis.html", "Combustível e gás"],
    ["luz-e-agua.html", "Luz e água"],
    ["churrasco.html", "Churrasco pra 6"],
    ["trabalho.html", "Salário e trabalho"],
    ["aluguel.html", "Aluguel"],
    ["aumentos-de-impostos.html", "Aumentos de impostos"]
  ];

  var UFS = {
    AC: ["Acre", "N"], AL: ["Alagoas", "NE"], AP: ["Amapá", "N"], AM: ["Amazonas", "N"],
    BA: ["Bahia", "NE"], CE: ["Ceará", "NE"], DF: ["Distrito Federal", "CO"], ES: ["Espírito Santo", "SD"],
    GO: ["Goiás", "CO"], MA: ["Maranhão", "NE"], MT: ["Mato Grosso", "CO"], MS: ["Mato Grosso do Sul", "CO"],
    MG: ["Minas Gerais", "SD"], PA: ["Pará", "N"], PB: ["Paraíba", "NE"], PR: ["Paraná", "S"],
    PE: ["Pernambuco", "NE"], PI: ["Piauí", "NE"], RJ: ["Rio de Janeiro", "SD"], RN: ["Rio Grande do Norte", "NE"],
    RS: ["Rio Grande do Sul", "S"], RO: ["Rondônia", "N"], RR: ["Roraima", "N"], SC: ["Santa Catarina", "S"],
    SP: ["São Paulo", "SD"], SE: ["Sergipe", "NE"], TO: ["Tocantins", "N"]
  };
  // Sudeste usa "SD" porque "SE" é a sigla de Sergipe
  var REGIOES = { N: "Norte", NE: "Nordeste", CO: "Centro-Oeste", SD: "Sudeste", S: "Sul" };
  var MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];

  function nomeLocal(cod) {
    if (cod === "BR") return "Brasil";
    if (REGIOES[cod]) return REGIOES[cod];
    if (UFS[cod]) return UFS[cod][0];
    return cod;
  }

  /* "no Brasil", "no Sudeste", "na Bahia", "em São Paulo"... */
  var NO = "AC AM AP CE DF ES MA MT MS PA PR PI RJ RN RS TO".split(" "), NA = ["BA", "PB"];
  function emLocal(cod) {
    var n = nomeLocal(cod);
    if (cod === "BR" || REGIOES[cod] || NO.indexOf(cod) > -1) return "no " + n;
    if (NA.indexOf(cod) > -1) return "na " + n;
    return "em " + n;
  }

  /* Monta o seletor Brasil > regiões > estados, só com os códigos que têm dados. */
  function seletorLocal(sel, disponiveis, inicial) {
    var tem = function (c) { return !disponiveis || disponiveis.indexOf(c) > -1; };
    var html = "";
    if (tem("BR")) html += '<option value="BR">Brasil</option>';
    var grupoR = "";
    Object.keys(REGIOES).forEach(function (r) { if (tem(r)) grupoR += '<option data-tipo="regiao" value="' + r + '">' + REGIOES[r] + "</option>"; });
    if (grupoR) html += '<optgroup label="Regiões">' + grupoR + "</optgroup>";
    var grupoE = "";
    Object.keys(UFS).sort(function (a, b) { return UFS[a][0].localeCompare(UFS[b][0], "pt"); })
      .forEach(function (u) { if (tem(u)) grupoE += '<option value="' + u + '">' + UFS[u][0] + "</option>"; });
    if (grupoE) html += '<optgroup label="Estados e DF">' + grupoE + "</optgroup>";
    sel.innerHTML = html;
    if (inicial && tem(inicial)) sel.value = inicial;
    escolhaLocal(sel);
  }

  /* Escolha de local em painel próprio (no celular abre por baixo, como uma gaveta).
     O <select> continua na página, escondido: as páginas seguem lendo sel.value e o evento "change".
     Motivo: a lista nativa do celular não rolava bem com a lista de regiões e estados. */
  function escolhaLocal(sel) {
    if (!sel._escolha) {
      var btn = document.createElement("button");
      btn.type = "button"; btn.className = "escolha-btn"; btn.setAttribute("aria-haspopup", "dialog");
      btn.id = (sel.id || "local") + "-botao";
      sel.classList.add("visually-hidden"); sel.tabIndex = -1; sel.setAttribute("aria-hidden", "true");
      sel.insertAdjacentElement("afterend", btn);
      var lbl = sel.id && document.querySelector('label[for="' + sel.id + '"]');
      if (lbl) lbl.htmlFor = btn.id;
      // quando a página muda sel.value por código, o botão acompanha
      var desc = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, "value");
      Object.defineProperty(sel, "value", { configurable: true,
        get: function () { return desc.get.call(this); },
        set: function (v) { desc.set.call(this, v); atualizar(); } });
      sel.addEventListener("change", atualizar);
      btn.addEventListener("click", abrir);
      sel._escolha = { btn: btn };
    }
    var botao = sel._escolha.btn;
    function atualizar() {
      var o = sel.options[sel.selectedIndex];
      botao.innerHTML = (o ? iconeOpcao(o) : '<span class="escolha-ico" aria-hidden="true">◎</span>') +
        "<span>" + (o ? o.textContent : "Escolha o local") + '</span><svg width="12" height="8" viewBox="0 0 12 8" aria-hidden="true"><path d="M1 1l5 5 5-5" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>';
    }
    function abrir() {
      var grupos = [{ nome: "", itens: [] }];
      [].forEach.call(sel.children, function (n) {
        if (n.tagName === "OPTGROUP") grupos.push({ nome: n.label, itens: [].slice.call(n.children) });
        else grupos[0].itens.push(n);
      });
      var atual = sel.value;
      var fundo = document.createElement("div");
      fundo.className = "escolha";
      fundo.innerHTML = '<div class="escolha-painel" role="dialog" aria-modal="true" aria-label="Escolha o local">' +
        '<div class="escolha-topo"><b>Onde você mora?</b><button type="button" class="escolha-fechar" aria-label="Fechar">✕</button></div>' +
        '<input type="search" class="escolha-busca" placeholder="Buscar estado ou região" aria-label="Buscar estado ou região">' +
        '<div class="escolha-lista">' + grupos.filter(function (g) { return g.itens.length; }).map(function (g) {
          return (g.nome ? '<p class="escolha-grupo">' + g.nome + "</p>" : "") + '<div class="escolha-itens' + (g.itens.length > 6 ? " muitos" : "") + '">' +
            g.itens.map(function (o) {
              return '<button type="button" data-v="' + o.value + '" aria-pressed="' + (o.value === atual) + '">' + iconeOpcao(o) + "<span>" + o.textContent + "</span></button>";
            }).join("") + "</div>";
        }).join("") + "</div></div>";
      document.body.appendChild(fundo);
      document.documentElement.classList.add("escolha-aberta");
      var busca = fundo.querySelector(".escolha-busca");
      function fechar() { fundo.remove(); document.documentElement.classList.remove("escolha-aberta"); document.removeEventListener("keydown", tecla); botao.focus(); }
      function tecla(e) { if (e.key === "Escape") fechar(); }
      document.addEventListener("keydown", tecla);
      fundo.addEventListener("click", function (e) {
        if (e.target === fundo || e.target.closest(".escolha-fechar")) return fechar();
        var b = e.target.closest("button[data-v]"); if (!b) return;
        if (b.dataset.v !== sel.value) { sel.value = b.dataset.v; sel.dispatchEvent(new Event("change", { bubbles: true })); }
        fechar();
      });
      busca.addEventListener("input", function () {
        var q = busca.value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
        [].forEach.call(fundo.querySelectorAll("button[data-v]"), function (b) {
          b.hidden = q && b.textContent.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().indexOf(q) < 0 && b.dataset.v.toLowerCase() !== q;
        });
      });
      var marcado = fundo.querySelector('[aria-pressed="true"]');
      if (marcado) marcado.scrollIntoView({ block: "center" });
      // no celular não abre o teclado sozinho (cobriria a lista); no computador já dá para digitar
      if (window.matchMedia("(hover: hover)").matches) busca.focus(); else (marcado || fundo.querySelector("button[data-v]")).focus({ preventScroll: true });
    }
    atualizar();
  }

  function lembrar(chave, valor) {
    try { if (valor === undefined) return localStorage.getItem("cvb-" + chave); localStorage.setItem("cvb-" + chave, valor); } catch (e) { return null; }
  }

  /* ---------- Formatação ---------- */
  function brl(v, casas) {
    if (v === null || v === undefined || isNaN(v)) return "—";
    if (casas === undefined) casas = Math.abs(v) >= 1000 ? 0 : 2;
    return "R$ " + v.toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas });
  }
  function numero(v, casas) {
    if (v === null || v === undefined || isNaN(v)) return "—";
    return v.toLocaleString("pt-BR", { minimumFractionDigits: casas || 0, maximumFractionDigits: casas || 0 });
  }
  function pct(v, casas) {
    if (v === null || v === undefined || isNaN(v)) return "—";
    return (v > 0 ? "+" : "") + v.toLocaleString("pt-BR", { minimumFractionDigits: casas === undefined ? 1 : casas, maximumFractionDigits: casas === undefined ? 1 : casas }) + "%";
  }
  function milhoes(v) {
    if (v === null || v === undefined || isNaN(v)) return "—";
    return (v / 1e6).toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + " milhões";
  }
  /* "2026-09" → "set/2026"; "2026-09-14" → "14/09/2026"; "2026-T2" → "2º tri/2026" */
  function data(s) {
    if (!s) return "—";
    var m = /^(\d{4})-T(\d)$/.exec(s);
    if (m) return m[2] + "º tri/" + m[1];
    m = /^(\d{4})-(\d{2})$/.exec(s);
    if (m) return MESES[+m[2] - 1] + "/" + m[1];
    m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s);
    if (m) return m[3] + "/" + m[2] + "/" + m[1];
    return s;
  }
  function horas(h) {
    if (h === null || h === undefined || isNaN(h)) return "—";
    var hh = Math.floor(h), mm = Math.round((h - hh) * 60);
    if (mm === 60) { hh += 1; mm = 0; }
    return hh + " h " + (mm < 10 ? "0" : "") + mm + " min";
  }
  /* Cores e setas em todo o site: preço que sobe = vermelho com seta para cima; preço que desce = verde com
     seta para baixo. Para salário e poder de compra é o contrário (bomSubir = true): subir é verde. */
  function classe(dif, bomSubir) {
    if (dif === null || dif === undefined || isNaN(dif) || Math.abs(dif) < 1e-9) return "igual";
    return ((dif > 0) !== !!bomSubir) ? "sobe" : "desce";
  }
  function flecha(dif) {
    if (dif === null || dif === undefined || isNaN(dif)) return "";
    if (Math.abs(dif) < 1e-9) return "= ";
    return dif > 0 ? "▲ " : "▼ ";
  }
  /* Variação em %, com seta e cor. variacao(12.7) → <span class="d sobe">▲ 12,7%</span> */
  function variacao(v, opts) {
    opts = opts || {};
    if (v === null || v === undefined || isNaN(v)) return '<span class="d igual">—</span>';
    var casas = opts.casas === undefined ? 1 : opts.casas;
    if (Math.abs(v) < Math.pow(10, -casas) / 2) v = 0;
    return '<span class="d ' + classe(v, opts.bomSubir) + '">' + flecha(v) +
      Math.abs(v).toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas }) + "%" + (opts.sufixo || "") + "</span>";
  }
  /* Variação em valor e em %, juntas, com seta e cor: ▲ R$ 0,05 · 0,87%
     dif = diferença em valor; fmtAbs formata o valor (sem sinal). Usado no dólar, Ibovespa e ações. */
  function varDupla(dif, pct, fmtAbs, opts) {
    opts = opts || {};
    if (dif === null || dif === undefined || isNaN(dif) || pct === null || pct === undefined || isNaN(pct)) return '<span class="d vd igual">—</span>';
    var cls = Math.abs(pct) < 0.005 ? "igual" : classe(dif, opts.bomSubir);
    var seta = cls === "igual" ? "= " : dif > 0 ? "▲ " : "▼ ";
    return '<span class="d vd ' + cls + '"><span class="vt">' + seta.trim() + '</span><span class="va">' + fmtAbs(Math.abs(dif)) + '</span><span class="vp">' +
      Math.abs(pct).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + "%</span>" + (opts.sufixo ? '<span class="vs">' + opts.sufixo + "</span>" : "") + "</span>";
  }

  /* Diferença em valor (ex.: R$ 0,01 na semana), com seta e cor. */
  function seta(atual, anterior, fmt, sufixo, bomSubir) {
    if (atual === null || anterior === null || atual === undefined || anterior === undefined) return '<span class="d igual">sem comparação</span>';
    var dif = atual - anterior;
    if (Math.abs(dif) < 0.005) return '<span class="d igual">= sem mudança' + (sufixo || "") + "</span>";
    return '<span class="d ' + classe(dif, bomSubir) + '">' + flecha(dif) + fmt(Math.abs(dif)) + (sufixo || "") + "</span>";
  }

  /* Gráfico pequeno para os cartões: linha, área, linhas-guia com valores e datas de início e fim.
     As linhas são SVG esticado na largura do cartão; os textos são HTML, para não deformar. */
  function mini(serie, n, fmt) {
    if (!serie || serie.length < 2) return "";
    var pts = serie.slice(-(n || 48)).filter(function (p) { return p[1] !== null; });
    if (pts.length < 2) return "";
    var ys = pts.map(function (p) { return p[1]; });
    var ticks = escalaBonita(Math.min.apply(null, ys), Math.max.apply(null, ys), 2);
    var y0 = ticks[0], y1 = ticks[ticks.length - 1], W = 300, H = 100;
    var passo = ticks.length > 1 ? ticks[1] - ticks[0] : 1;
    fmt = fmt || function (v) { return numero(v, passo >= 1 ? 0 : 2); };
    var px = function (i) { return i / (pts.length - 1) * W; };
    var py = function (v) { return (1 - (v - y0) / (y1 - y0)) * H; };
    var d = pts.map(function (p, i) { return (i ? "L" : "M") + px(i).toFixed(1) + " " + py(p[1]).toFixed(1); }).join(" ");
    var guias = ticks.map(function (t) { return '<line x1="0" x2="' + W + '" y1="' + py(t).toFixed(1) + '" y2="' + py(t).toFixed(1) + '" stroke="#2E3531" vector-effect="non-scaling-stroke"/>'; }).join("");
    var rot = ticks.map(function (t) { return '<span class="my" style="top:' + (py(t) / H * 100).toFixed(1) + '%">' + fmt(t) + "</span>"; }).join("");
    var mes = function (k) { var m = /^(\d{4})-(\d{2})/.exec(k); return m ? MESES[+m[2] - 1] + "/" + m[1].slice(2) : k; };
    var u = pts[pts.length - 1];
    return '<div class="mini-g" aria-hidden="true"><div class="mini-a">' +
      '<svg viewBox="0 0 ' + W + " " + H + '" preserveAspectRatio="none">' + guias +
      '<path d="' + d + " L" + W + " " + H + " L0 " + H + ' Z" fill="currentColor" opacity=".10"/>' +
      '<path d="' + d + '" fill="none" stroke="currentColor" stroke-width="2" vector-effect="non-scaling-stroke" stroke-linejoin="round"/></svg>' +
      '<i class="mponto" style="top:' + (py(u[1]) / H * 100).toFixed(1) + '%"></i>' + rot +
      '<span class="mx" style="left:0">' + mes(pts[0][0]) + '</span><span class="mx" style="right:0">' + mes(u[0]) + "</span></div></div>";
  }

  /* Barra verde e amarela de impostos: valor em R$ nas duas partes e % na amarela. */
  function barraImpostos(semImp, imposto, rotulo) {
    var total = semImp + imposto, p = total > 0 ? Math.max(0, Math.min(100, imposto / total * 100)) : 0;
    return '<div class="p1" style="flex:' + (100 - p).toFixed(2) + ' 1 0" title="' + rotulo + '"><span class="r">' + rotulo + '</span><b>' + brl(semImp, 2) + "</b></div>" +
      '<div class="p2" style="flex:' + p.toFixed(2) + ' 1 0" title="Impostos"><span class="r">Impostos ' + numero(p, 0) + "%</span><b>" + brl(imposto, 2) + "</b></div>";
  }

  /* Bandeira do estado (imagens em assets/bandeiras). */
  /* Ícone de uma opção do seletor: bandeira do Brasil, mapa com a região em destaque, ou bandeira do estado.
     */
  function iconeOpcao(o) {
    if (o.value === "BR") return bandeira("BR");
    if (o.dataset.tipo === "regiao") return iconeRegiao(o.value);
    return bandeira(o.value);
  }
  function iconeRegiao(r) {
    if (!REGIOES[r]) return "";
    return '<img class="bandeira mapa" src="assets/bandeiras/regiao-' + r + '.png" alt="" width="23" height="16" loading="lazy">';
  }

  function bandeira(uf) {
    if (!UFS[uf] && uf !== "BR") return "";
    return '<img class="bandeira" src="assets/bandeiras/' + uf + '.png" alt="" width="23" height="16" loading="lazy">';
  }

  /* Arquivos de config/ (editados à mão). */
  var cacheCfg = {};
  function config(nome) {
    if (!cacheCfg[nome]) cacheCfg[nome] = fetch("config/" + nome + ".json", { cache: "no-cache" })
      .then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; });
    return cacheCfg[nome];
  }

  /* ---------- Séries ---------- */
  function ultimo(serie) { if (!serie || !serie.length) return null; return serie[serie.length - 1]; }
  function anterior(serie, n) { if (!serie || serie.length <= (n || 1)) return null; return serie[serie.length - 1 - (n || 1)]; }
  function valorEm(serie, chave) {
    if (!serie) return null;
    for (var i = serie.length - 1; i >= 0; i--) if (serie[i][0] <= chave) return serie[i][1];
    return null;
  }
  function variacao12(serie) {
    var u = ultimo(serie); if (!u) return null;
    var alvo;
    if (/^\d{4}-\d{2}$/.test(u[0])) { var a = +u[0].slice(0, 4) - 1; alvo = a + u[0].slice(4); }
    else if (/^\d{4}-\d{2}-\d{2}$/.test(u[0])) { alvo = (+u[0].slice(0, 4) - 1) + u[0].slice(4); }
    else return null;
    var base = null;
    for (var i = 0; i < serie.length; i++) if (serie[i][0] <= alvo) base = serie[i][1];
    if (!base) return null;
    return (u[1] / base - 1) * 100;
  }

  /* ---------- Dados ---------- */
  var cache = {};
  function carregar(nome) {
    if (cache[nome]) return cache[nome];
    cache[nome] = fetch("dados/" + nome + ".json", { cache: "no-cache" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .catch(function () { return null; });
    return cache[nome];
  }

  /* ---------- Gráfico de linhas em SVG ---------- */
  // amarelo da etiqueta de preço primeiro; verde e vermelho ficam reservados para "desceu" e "subiu"
  var CORES = ["#FFD23F", "#7FB2F0", "#C4A3F5", "#ECEFED", "#F5B97F"];

  function escalaBonita(min, max, n) {
    if (min === max) { min -= 1; max += 1; }
    var bruto = (max - min) / n;
    var mag = Math.pow(10, Math.floor(Math.log10(bruto)));
    var passo = [1, 2, 2.5, 5, 10].map(function (f) { return f * mag; }).filter(function (p) { return p >= bruto; })[0];
    var ini = Math.floor(min / passo) * passo, fim = Math.ceil(max / passo) * passo;
    var t = []; for (var v = ini; v <= fim + passo / 2; v += passo) t.push(+v.toFixed(10));
    return t;
  }

  function grafico(alvo, series, opts) {
    opts = opts || {};
    var fmtY = opts.fmtY || function (v) { return numero(v, 2); };
    // desenha no tamanho real do espaço, para o texto não encolher no celular
    var W = Math.max(300, Math.round(alvo.clientWidth || 640)), H = opts.altura || Math.max(200, Math.min(300, Math.round(W * 0.45))), mE = 58, mD = 14, mT = 14, mB = 28;
    var rotK = opts.rotK || data;  // texto da data na dica e na tabela
    var rotX = opts.rotX || function (k) { var m = /^(\d{4})-(\d{2})-\d{2}$/.exec(k); return m ? MESES[+m[2] - 1] + "/" + m[1] : data(k); };
    var nX = Math.max(2, Math.min(6, Math.floor(W / 110)));
    series = series.filter(function (s) { return s.pontos && s.pontos.length; });
    if (!series.length) { alvo.innerHTML = '<p class="aviso">Ainda não há dados para este gráfico. Eles aparecem depois da próxima coleta.</p>'; return; }

    var xs = {};
    series.forEach(function (s) { s.pontos.forEach(function (p) { xs[p[0]] = 1; }); });
    var chaves = Object.keys(xs).sort();
    var idx = {}; chaves.forEach(function (k, i) { idx[k] = i; });
    var ys = []; series.forEach(function (s) { s.pontos.forEach(function (p) { if (p[1] !== null) ys.push(p[1]); }); });
    var ticks = escalaBonita(Math.min.apply(null, ys), Math.max.apply(null, ys), 4);
    var y0 = ticks[0], y1 = ticks[ticks.length - 1];
    var px = function (i) { return mE + (chaves.length === 1 ? (W - mE - mD) / 2 : i * (W - mE - mD) / (chaves.length - 1)); };
    var py = function (v) { return mT + (1 - (v - y0) / (y1 - y0)) * (H - mT - mB); };

    var s = '<svg viewBox="0 0 ' + W + " " + H + '" role="img" aria-label="' + (opts.titulo || "Gráfico") + '">';
    ticks.forEach(function (t) {
      s += '<line x1="' + mE + '" x2="' + (W - mD) + '" y1="' + py(t) + '" y2="' + py(t) + '" stroke="#262C29"/>';
      s += '<text x="' + (mE - 8) + '" y="' + (py(t) + 4) + '" fill="#929C97" font-size="11" font-family="IBM Plex Mono, monospace" text-anchor="end">' + fmtY(t) + "</text>";
    });
    // rótulos do eixo X: até 6, espaçados
    nX = Math.min(nX, chaves.length); var passoX = Math.max(1, Math.floor((chaves.length - 1) / Math.max(1, nX - 1)));
    for (var i = 0; i < chaves.length; i += passoX) {
      var anc = i === 0 ? "start" : "middle";
      if (chaves.length - 1 - i < passoX * 0.8 && i !== 0) continue;
      s += '<text x="' + px(i) + '" y="' + (H - 8) + '" fill="#929C97" font-size="11" font-family="Public Sans, sans-serif" text-anchor="' + anc + '">' + rotX(chaves[i]) + "</text>";
    }
    if (chaves.length > 1) s += '<text x="' + px(chaves.length - 1) + '" y="' + (H - 8) + '" fill="#929C97" font-size="11" font-family="Public Sans, sans-serif" text-anchor="end">' + rotX(chaves[chaves.length - 1]) + "</text>";
    (opts.marcos || []).forEach(function (m) {
      var k = chaves.filter(function (c) { return c >= m[0]; })[0];
      if (!k || k === chaves[0]) return;
      var x = px(idx[k]);
      s += '<line x1="' + x + '" x2="' + x + '" y1="' + mT + '" y2="' + (H - mB) + '" stroke="#929C97" stroke-dasharray="3 3"/>';
      s += '<text x="' + (x + 4) + '" y="' + (mT + 10) + '" fill="#929C97" font-size="10" font-family="Public Sans, sans-serif">' + m[1] + "</text>";
    });
    series.forEach(function (se, n) {
      var cor = se.cor || CORES[n % CORES.length];
      var d = "", area = "";
      se.pontos.forEach(function (p, j) {
        if (p[1] === null) return;
        d += (d ? " L" : "M") + px(idx[p[0]]).toFixed(1) + " " + py(p[1]).toFixed(1);
      });
      if (series.length === 1) {
        var pr = se.pontos[0], ul = se.pontos[se.pontos.length - 1];
        area = d + " L" + px(idx[ul[0]]).toFixed(1) + " " + (H - mB) + " L" + px(idx[pr[0]]).toFixed(1) + " " + (H - mB) + " Z";
        s += '<path d="' + area + '" fill="' + cor + '" opacity=".12"/>';
      }
      s += '<path d="' + d + '" fill="none" stroke="' + cor + '" stroke-width="2.5" stroke-linejoin="round"/>';
      var u = se.pontos[se.pontos.length - 1];
      s += '<circle cx="' + px(idx[u[0]]) + '" cy="' + py(u[1]) + '" r="4.5" fill="' + cor + '"/>';
    });
    s += '<line class="guia" x1="0" x2="0" y1="' + mT + '" y2="' + (H - mB) + '" stroke="#ECEFED" stroke-opacity=".35" visibility="hidden"/>';
    s += "</svg>";

    var legenda = series.length > 1 ? '<div class="rodape">' + series.map(function (se, n) {
      return '<span><i style="display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px;background:' + (se.cor || CORES[n % CORES.length]) + '"></i>' + se.nome + "</span>";
    }).join("") + "</div>" : "";

    // tabela equivalente, para leitores de tela e para quem prefere números
    var linhas = chaves.slice().reverse().map(function (k) {
      return "<tr><td>" + rotK(k) + "</td>" + series.map(function (se) {
        var p = se.pontos.filter(function (q) { return q[0] === k; })[0];
        return '<td class="r">' + (p ? fmtY(p[1]) : "—") + "</td>";
      }).join("") + "</tr>";
    }).join("");
    var tabela = '<details><summary>Ver os números em tabela</summary><div class="tabela" style="max-height:320px;overflow:auto;margin-top:8px"><table><thead><tr><th>Data</th>' +
      series.map(function (se) { return '<th class="r">' + se.nome + "</th>"; }).join("") + "</tr></thead><tbody>" + linhas + "</tbody></table></div></details>";

    alvo.style.position = "relative";
    alvo.innerHTML = s + legenda + tabela;
    alvo._grafico = [series, opts, W];
    if (desenhados.indexOf(alvo) < 0) desenhados.push(alvo);

    var svg = alvo.querySelector("svg"), guia = svg.querySelector(".guia");
    var dica = document.createElement("div"); dica.className = "tooltip"; dica.hidden = true; alvo.appendChild(dica);
    function mover(ev) {
      var r = svg.getBoundingClientRect();
      var x = (ev.clientX - r.left) / r.width * W;
      var i = Math.round((x - mE) / ((W - mE - mD) / Math.max(1, chaves.length - 1)));
      i = Math.max(0, Math.min(chaves.length - 1, i));
      var k = chaves[i];
      guia.setAttribute("x1", px(i)); guia.setAttribute("x2", px(i)); guia.setAttribute("visibility", "visible");
      var txt = rotK(k) + ": " + series.map(function (se) {
        var p = se.pontos.filter(function (q) { return q[0] === k; })[0];
        return (series.length > 1 ? se.nome + " " : "") + (p ? fmtY(p[1]) : "—");
      }).join(" · ");
      dica.textContent = txt; dica.hidden = false;
      // mantém a etiqueta inteira dentro do gráfico (não corta nas pontas)
      var ra = alvo.getBoundingClientRect(), larg = dica.offsetWidth, cx = px(i) / W * r.width;
      cx = Math.max(larg / 2, Math.min(r.width - larg / 2, cx));
      dica.style.left = (r.left - ra.left + cx) + "px";
      dica.style.top = (r.top - ra.top + mT / H * r.height + 8) + "px";
    }
    function esconder() { dica.hidden = true; guia.setAttribute("visibility", "hidden"); }
    // Celular: o dedo arrastando na horizontal mostra os valores (a página não rola);
    // na vertical a página rola normalmente. Ao soltar, a etiqueta fica até tocar fora.
    svg.style.touchAction = "pan-y";
    svg.addEventListener("pointerdown", function (ev) {
      if (ev.pointerType !== "mouse") { try { svg.setPointerCapture(ev.pointerId); } catch (e) {} }
      mover(ev);
    });
    svg.addEventListener("pointermove", mover);
    svg.addEventListener("pointerleave", function (ev) { if (ev.pointerType === "mouse") esconder(); });
    alvo._esconder = esconder;
  }

  // tocar fora de um gráfico esconde a etiqueta de valor
  document.addEventListener("pointerdown", function (ev) {
    desenhados.forEach(function (el) { if (el._esconder && !el.contains(ev.target)) el._esconder(); });
  });

  // redesenha os gráficos quando a largura muda (girar o celular, por exemplo)
  var desenhados = [], espera;
  window.addEventListener("resize", function () {
    clearTimeout(espera);
    espera = setTimeout(function () {
      desenhados.forEach(function (el) {
        var g = el._grafico;
        if (g && el.isConnected && Math.abs((el.clientWidth || 0) - g[2]) > 40) grafico(el, g[0], g[1]);
      });
    }, 200);
  });

  /* ---------- Topo e rodapé ---------- */
  function montarMoldura() {
    var aqui = location.pathname.split("/").pop() || "index.html";
    var topo = document.createElement("header");
    topo.className = "topo";
    topo.innerHTML = '<div class="wrap"><a class="logo" href="index.html" aria-label="' + SITE.nome + ' · início"><img src="assets/logo.png" alt="' + SITE.nome + '" width="261" height="56"></a><nav class="menu" aria-label="Seções do site">' +
      MENU.map(function (m) { return '<a href="' + m[0] + '"' + (m[0] === aqui ? ' aria-current="page"' : "") + ">" + m[1] + "</a>"; }).join("") + "</nav></div>";
    document.body.insertBefore(topo, document.body.firstChild);
    cotacoesTopo(topo.querySelector(".logo"), aqui === "mercado.html");

    var rod = document.createElement("footer");
    rod.className = "rodape-site";
    rod.innerHTML = '<div class="wrap"><a class="destaque" href="como-calculamos.html">Como calculamos</a>' +
      '<a href="como-calculamos.html#fontes">Fontes</a><a href="https://github.com/' + (document.documentElement.dataset.repo || "") + '/tree/main/dados">Dados abertos</a>' +
      '<a href="privacidade.html">Privacidade</a><a href="como-calculamos.html#erro">Encontrou um erro?</a>' +
      '<span class="visitas" id="visitas" title="Visitas ao site" hidden></span>' +
      '<p class="fonte">Dados de DIEESE, ANP, IBGE e outras fontes oficiais, citadas em cada número. Valores marcados como “estimado” são calculados por nós.</p></div>';
    document.body.appendChild(rod);

    if (SITE.contador) {
      var sc = document.createElement("script");
      sc.async = true; sc.src = "//gc.zgo.at/count.js"; sc.setAttribute("data-goatcounter", SITE.contador + "/count");
      document.body.appendChild(sc);
      fetch(SITE.contador + "/counter/TOTAL.json").then(function (r) { return r.ok ? r.json() : null; }).then(function (j) {
        if (!j || !j.count) return;
        var el = document.getElementById("visitas"); el.textContent = j.count; el.hidden = false;
      }).catch(function () {});
    }
  }

  /* ---------- Dólar e Ibovespa no canto do topo (levam à página mercado.html) ----------
     O arquivo dados/mercado-agora.json é atualizado de hora em hora no pregão (B3 com ~15 min de atraso).
     O dólar ainda tenta o valor do momento na AwesomeAPI (gratuita); se ela falhar, fica o do arquivo.
     Cores: dólar subindo é vermelho (encarece o que compramos); Bolsa subindo é verde. */
  function dolarAoVivo() {
    try { var c = JSON.parse(sessionStorage.getItem("cvb-usd") || "null"); if (c && Date.now() - c.t < 120000) return Promise.resolve(c.v); } catch (e) {}
    return fetch("https://economia.awesomeapi.com.br/json/last/USD-BRL").then(function (r) { return r.ok ? r.json() : null; }).then(function (j) {
      var q = j && j.USDBRL; if (!q || !(+q.bid > 0)) return null;
      var v = { preco: +q.bid, pct: +q.pctChange, dif: +q.varBid, hora: new Date(+q.timestamp * 1000).toISOString() };
      try { sessionStorage.setItem("cvb-usd", JSON.stringify({ t: Date.now(), v: v })); } catch (e) {}
      return v;
    }).catch(function () { return null; });
  }
  function cotacoesTopo(depoisDe, aqui) {
    var a = document.createElement("a");
    a.className = "cotas"; a.href = "mercado.html"; a.hidden = true;
    if (aqui) a.setAttribute("aria-current", "page");
    a.setAttribute("aria-label", "Dólar e Ibovespa: ver gráficos e ações das estatais");
    depoisDe.insertAdjacentElement("afterend", a);
    function item(rot, curto, valor, dif, pct, fmtAbs, bomSubir) {
      return '<span class="cota"><span class="cn"><span class="cn-l">' + rot + '</span><span class="cn-c">' + curto + "</span></span><b>" + valor + "</b>" +
        varDupla(dif, pct, fmtAbs, { bomSubir: bomSubir }) + "</span>";
    }
    var f3 = function (v) { return numero(v, 3); }, f0 = function (v) { return numero(v, 0); };
    Promise.all([carregar("mercado-agora"), dolarAoVivo()]).then(function (r) {
      var m = (r[0] && r[0].ativos) || {}, vivo = r[1], h = "";
      var usd = m.USD, ib = m.IBOV;
      if (vivo) h += item("Dólar", "USD", brl(vivo.preco, 2), isNaN(vivo.dif) ? vivo.preco - vivo.preco / (1 + vivo.pct / 100) : vivo.dif, vivo.pct, f3, false);
      else if (usd && usd.preco) h += item("Dólar", "USD", brl(usd.preco, 2), usd.anterior ? usd.preco - usd.anterior : null, usd.anterior ? (usd.preco / usd.anterior - 1) * 100 : null, f3, false);
      if (ib && ib.preco) h += item("Ibovespa", "Ibov", numero(ib.preco, 0), ib.anterior ? ib.preco - ib.anterior : null, ib.anterior ? (ib.preco / ib.anterior - 1) * 100 : null, f0, true);
      if (!h) return;
      a.innerHTML = h; a.hidden = false;
    });
  }

  /* ---------- Animações (sutis; desligadas para quem pede menos movimento) ----------
     - cartões, gráficos e tabelas aparecem com um leve deslize ao entrar na tela
     - gráficos se desenham da esquerda para a direita
     - barras crescem
     - números da etiqueta amarela contam até o valor
     Tudo é aplicado a elementos novos automaticamente, mesmo os que as páginas desenham depois. */
  var semMovimento = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var ALVOS = ".card, .fato, .grafico, .tabela, .itens, .explica, .churras, .impostos, .tag, .la-card, .hist-band, .ufs, .band-tar, .bloco > h2, .titulo-filtro";
  // itens de lista que entram um depois do outro
  var CASCATA = "tbody > tr, .itens > .item, .ufs > .uf, .hist-band .c, .painel .lista li, .cards > .card, .la-cards > .la-card";
  // números que contam (só elementos sem filhos, para não apagar setas e etiquetas internas)
  var NUMEROS = ".val, .num, .v, .lista b, td.r, .item .r, .fato .num .d, .uf .v";

  function contar(el) {
    if (el._contado) return; el._contado = true;
    var txt = el.textContent, m = /\d[\d.]*(,\d+)?/.exec(txt);
    if (!m) return;
    var bruto = m[0], casas = m[1] ? m[1].length - 1 : 0, milhar = bruto.indexOf(".") > -1;
    var alvo = parseFloat(bruto.replace(/\./g, "").replace(",", "."));
    if (!isFinite(alvo) || alvo === 0) return;
    var antes = txt.slice(0, m.index), depois = txt.slice(m.index + bruto.length);
    var ini = alvo * (alvo > 50 ? 0.6 : 0), t0 = null, dur = 1100, ultimo = txt;
    function passo(t) {
      // se a página trocou o valor no meio (ex.: mudou o estado), para de contar
      if (!el.isConnected || el.textContent !== ultimo) return;
      if (t0 === null) t0 = t;
      var k = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(1 - k, 3);
      var v = k < 1 ? ini + (alvo - ini) * e : alvo;
      el.textContent = ultimo = antes + v.toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas, useGrouping: milhar }) + depois;
      if (k < 1) requestAnimationFrame(passo);
    }
    requestAnimationFrame(passo);
  }

  function contarDentro(el) {
    var lista = el.matches(NUMEROS) ? [el] : [];
    lista = lista.concat([].slice.call(el.querySelectorAll(NUMEROS)));
    lista.slice(0, 120).forEach(function (n) { if (!n.children.length) contar(n); });
  }
  function mostrar(el) {
    el.classList.add("visivel");
    contarDentro(el);
  }
  function numerar(raiz) {
    var lista = raiz.matches && raiz.matches(CASCATA) ? [raiz] : [];
    if (raiz.querySelectorAll) lista = lista.concat([].slice.call(raiz.querySelectorAll(CASCATA)));
    lista.forEach(function (el) {
      var i = 0, x = el; while ((x = x.previousElementSibling) && i < 40) i++;
      el.style.setProperty("--i", i);
      // linha nova numa tabela que já está na tela (ex.: trocou o filtro): conta os números dela também
      var pai = el.parentElement && el.parentElement.closest(".visivel");
      if (pai) contarDentro(el);
    });
  }

  function iniciarAnimacoes() {
    if (semMovimento || !("IntersectionObserver" in window)) return;
    document.documentElement.classList.add("anima");
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) { mostrar(e.target); io.unobserve(e.target); } });
    }, { rootMargin: "0px 0px -6% 0px", threshold: 0.08 });
    function preparar(raiz) {
      numerar(raiz);
      var lista = raiz.matches && raiz.matches(ALVOS) ? [raiz] : [];
      if (raiz.querySelectorAll) lista = lista.concat([].slice.call(raiz.querySelectorAll(ALVOS)));
      lista.forEach(function (el) {
        if (el._anim) return; el._anim = true;
        el.classList.add("aparece");
        // atraso em cascata entre irmãos (cartões lado a lado)
        var i = 0, x = el; while ((x = x.previousElementSibling) && i < 6) i++;
        el.style.setProperty("--atraso", (i * 90) + "ms");
        io.observe(el);
      });
      // gráfico redesenhado dentro de um bloco que já está visível
      if (raiz.closest) { var pai = raiz.closest(".visivel"); if (pai && raiz !== pai) [].forEach.call(raiz.querySelectorAll ? raiz.querySelectorAll(ALVOS) : [], mostrar); }
    }
    preparar(document.body);
    new MutationObserver(function (ms) {
      ms.forEach(function (m) { [].forEach.call(m.addedNodes, function (n) { if (n.nodeType === 1) preparar(n); }); });
    }).observe(document.body, { childList: true, subtree: true });
  }

  /* ---------- Foto pequena no canto de cada cartão ----------
     Fotos do Wikimedia Commons com licença livre (créditos em como-calculamos.html),
     recortadas em 200x200 e guardadas em assets/fotos/. O cartão é reconhecido pelo título;
     cartões com bandeira de estado/região ficam sem foto para não poluir. */
  // a ordem importa: o primeiro que bater no título vale
  var QUAL_DESENHO = [
    [/imposto/, "imposto"], [/cesta/, "cesta"], [/gasolina|etanol|diesel|combust/, "bomba"],
    [/gas de cozinha|botij/, "botijao"], [/churrasco/, "churrasco"], [/bandeira/, "bandeira"],
    [/luz|energia/, "luz"], [/agua/, "agua"], [/reajuste/, "contrato"], [/aluguel/, "casa"],
    [/carro/, "carro"], [/desemprego/, "trabalho"], [/salario|ganha|renda/, "dinheiro"],
    [/bolso/, "carteira"], [/dolar/, "dolar"], [/ibovespa|bolsa/, "bolsa"], [/petrobras/, "petroleo"],
    [/caixa/, "caixa"], [/banco|bb /, "banco"]
  ];
  var CARTOES = ".card, .la-card";
  function desenharCartao(el) {
    var t = el.querySelector(".t");
    if (!t || el.querySelector(".uf, .bandeira, img")) return;
    var txt = t.textContent.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
    var achou = QUAL_DESENHO.filter(function (q) { return q[0].test(txt); })[0];
    var velho = el.querySelector(":scope > .ico-card");
    if (velho && (!achou || velho.dataset.d !== achou[1])) { velho.remove(); velho = null; }
    if (!achou || velho) return;
    var s = document.createElement("span");
    s.className = "ico-card"; s.dataset.d = achou[1]; s.setAttribute("aria-hidden", "true");
    s.innerHTML = '<img src="assets/fotos/' + achou[1] + '.jpg" alt="" loading="lazy" decoding="async" width="200" height="200">';
    el.insertBefore(s, el.firstChild);
  }
  function desenharCartoes(raiz) {
    if (!raiz.querySelectorAll) return;
    var lista = raiz.matches(CARTOES) ? [raiz] : [];
    if (raiz.closest && raiz.parentElement) { var pai = raiz.parentElement.closest(CARTOES); if (pai) lista.push(pai); }
    lista.concat([].slice.call(raiz.querySelectorAll(CARTOES))).forEach(desenharCartao);
  }
  function iniciarDesenhos() {
    desenharCartoes(document.body);
    new MutationObserver(function (ms) {
      ms.forEach(function (m) { [].forEach.call(m.addedNodes, function (n) { if (n.nodeType === 1 && !n.classList.contains("ico-card")) desenharCartoes(n); }); });
    }).observe(document.body, { childList: true, subtree: true });
  }

  document.addEventListener("DOMContentLoaded", montarMoldura);
  document.addEventListener("DOMContentLoaded", iniciarDesenhos);
  document.addEventListener("DOMContentLoaded", iniciarAnimacoes);

  /* Transição entre páginas: a página atual some rápido antes de abrir a próxima. */
  document.addEventListener("click", function (e) {
    if (semMovimento || e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    var a = e.target.closest && e.target.closest("a[href]");
    if (!a || a.target || a.hasAttribute("download")) return;
    var url = new URL(a.href, location.href);
    if (url.origin !== location.origin || !/\.html$|\/$/.test(url.pathname) || (url.pathname === location.pathname && url.hash)) return;
    e.preventDefault();
    document.documentElement.classList.add("saindo");
    setTimeout(function () { location.href = url.href; }, 220);
  });
  // ao voltar pelo botão "voltar" do navegador, a página não pode ficar apagada
  window.addEventListener("pageshow", function () { document.documentElement.classList.remove("saindo"); });

  window.CVB = {
    SITE: SITE, UFS: UFS, REGIOES: REGIOES, nomeLocal: nomeLocal, emLocal: emLocal, seletorLocal: seletorLocal, lembrar: lembrar,
    brl: brl, numero: numero, pct: pct, milhoes: milhoes, data: data, horas: horas, seta: seta, variacao: variacao, varDupla: varDupla, classe: classe,
    mini: mini, bandeira: bandeira, iconeRegiao: iconeRegiao, config: config, barraImpostos: barraImpostos,
    ultimo: ultimo, anterior: anterior, valorEm: valorEm, variacao12: variacao12,
    carregar: carregar, grafico: grafico, dolarAoVivo: dolarAoVivo, MESES: MESES
  };
})();
