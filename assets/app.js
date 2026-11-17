/* Funções comuns a todas as páginas. Sem dependências externas. */
(function () {
  "use strict";

  var SITE = {
    nome: "Custo de Vida Brasil",
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
    BA: ["Bahia", "NE"], CE: ["Ceará", "NE"], DF: ["Distrito Federal", "CO"], ES: ["Espírito Santo", "SE"],
    GO: ["Goiás", "CO"], MA: ["Maranhão", "NE"], MT: ["Mato Grosso", "CO"], MS: ["Mato Grosso do Sul", "CO"],
    MG: ["Minas Gerais", "SE"], PA: ["Pará", "N"], PB: ["Paraíba", "NE"], PR: ["Paraná", "S"],
    PE: ["Pernambuco", "NE"], PI: ["Piauí", "NE"], RJ: ["Rio de Janeiro", "SE"], RN: ["Rio Grande do Norte", "NE"],
    RS: ["Rio Grande do Sul", "S"], RO: ["Rondônia", "N"], RR: ["Roraima", "N"], SC: ["Santa Catarina", "S"],
    SP: ["São Paulo", "SE"], SE: ["Sergipe", "NE"], TO: ["Tocantins", "N"]
  };
  var REGIOES = { N: "Norte", NE: "Nordeste", CO: "Centro-Oeste", SE: "Sudeste", S: "Sul" };
  var MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];

  function nomeLocal(cod) {
    if (cod === "BR") return "Brasil";
    if (REGIOES[cod]) return REGIOES[cod];
    if (UFS[cod]) return UFS[cod][0];
    return cod;
  }

  /* Monta o seletor Brasil > regiões > estados, só com os códigos que têm dados. */
  function seletorLocal(sel, disponiveis, inicial) {
    var tem = function (c) { return !disponiveis || disponiveis.indexOf(c) > -1; };
    var html = "";
    if (tem("BR")) html += '<option value="BR">Brasil</option>';
    var grupoR = "";
    Object.keys(REGIOES).forEach(function (r) { if (tem(r)) grupoR += '<option value="' + r + '">' + REGIOES[r] + "</option>"; });
    if (grupoR) html += '<optgroup label="Regiões">' + grupoR + "</optgroup>";
    var grupoE = "";
    Object.keys(UFS).sort(function (a, b) { return UFS[a][0].localeCompare(UFS[b][0], "pt"); })
      .forEach(function (u) { if (tem(u)) grupoE += '<option value="' + u + '">' + UFS[u][0] + "</option>"; });
    if (grupoE) html += '<optgroup label="Estados e DF">' + grupoE + "</optgroup>";
    sel.innerHTML = html;
    if (inicial && tem(inicial)) sel.value = inicial;
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
  function bandeira(uf) {
    if (!UFS[uf]) return "";
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
    var rotX = function (k) { var m = /^(\d{4})-(\d{2})-\d{2}$/.exec(k); return m ? MESES[+m[2] - 1] + "/" + m[1] : data(k); };
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
      return "<tr><td>" + data(k) + "</td>" + series.map(function (se) {
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
      var txt = data(k) + ": " + series.map(function (se) {
        var p = se.pontos.filter(function (q) { return q[0] === k; })[0];
        return (series.length > 1 ? se.nome + " " : "") + (p ? fmtY(p[1]) : "—");
      }).join(" · ");
      dica.textContent = txt; dica.hidden = false;
      dica.style.left = (px(i) / W * r.width) + "px";
      dica.style.top = (mT / H * r.height + 8) + "px";
    }
    svg.addEventListener("pointermove", mover);
    svg.addEventListener("pointerleave", function () { dica.hidden = true; guia.setAttribute("visibility", "hidden"); });
  }

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
    topo.innerHTML = '<div class="wrap"><a class="logo" href="index.html"><i aria-hidden="true"></i>' + SITE.nome + '</a><nav class="menu" aria-label="Seções do site">' +
      MENU.map(function (m) { return '<a href="' + m[0] + '"' + (m[0] === aqui ? ' aria-current="page"' : "") + ">" + m[1] + "</a>"; }).join("") + "</nav></div>";
    document.body.insertBefore(topo, document.body.firstChild);

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

  /* ---------- Animações (sutis; desligadas para quem pede menos movimento) ----------
     - cartões, gráficos e tabelas aparecem com um leve deslize ao entrar na tela
     - gráficos se desenham da esquerda para a direita
     - barras crescem
     - números da etiqueta amarela contam até o valor
     Tudo é aplicado a elementos novos automaticamente, mesmo os que as páginas desenham depois. */
  var semMovimento = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var ALVOS = ".card, .fato, .grafico, .tabela, .itens, .explica, .churras, .impostos, .tag";

  function contar(el) {
    if (el._contado) return; el._contado = true;
    var txt = el.textContent, m = /\d[\d.]*(,\d+)?/.exec(txt);
    if (!m) return;
    var bruto = m[0], casas = m[1] ? m[1].length - 1 : 0, milhar = bruto.indexOf(".") > -1;
    var alvo = parseFloat(bruto.replace(/\./g, "").replace(",", "."));
    if (!isFinite(alvo) || alvo === 0) return;
    var antes = txt.slice(0, m.index), depois = txt.slice(m.index + bruto.length);
    var ini = alvo * 0.8, t0 = null, dur = 700, ultimo = txt;
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

  function mostrar(el) {
    el.classList.add("visivel");
    if (el.classList.contains("tag")) { var v = el.querySelector(".val"); if (v) contar(v); }
  }

  function iniciarAnimacoes() {
    if (semMovimento || !("IntersectionObserver" in window)) return;
    document.documentElement.classList.add("anima");
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) { mostrar(e.target); io.unobserve(e.target); } });
    }, { rootMargin: "0px 0px -6% 0px", threshold: 0.08 });
    function preparar(raiz) {
      var lista = raiz.matches && raiz.matches(ALVOS) ? [raiz] : [];
      if (raiz.querySelectorAll) lista = lista.concat([].slice.call(raiz.querySelectorAll(ALVOS)));
      lista.forEach(function (el) {
        if (el._anim) return; el._anim = true;
        el.classList.add("aparece");
        // atraso em cascata entre irmãos (cartões lado a lado)
        var i = 0, x = el; while ((x = x.previousElementSibling) && i < 6) i++;
        el.style.setProperty("--atraso", (i * 60) + "ms");
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

  document.addEventListener("DOMContentLoaded", montarMoldura);
  document.addEventListener("DOMContentLoaded", iniciarAnimacoes);

  window.CVB = {
    SITE: SITE, UFS: UFS, REGIOES: REGIOES, nomeLocal: nomeLocal, seletorLocal: seletorLocal, lembrar: lembrar,
    brl: brl, numero: numero, pct: pct, milhoes: milhoes, data: data, horas: horas, seta: seta, variacao: variacao, classe: classe,
    mini: mini, bandeira: bandeira, config: config, barraImpostos: barraImpostos,
    ultimo: ultimo, anterior: anterior, valorEm: valorEm, variacao12: variacao12,
    carregar: carregar, grafico: grafico
  };
})();
