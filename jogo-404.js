/* Minijogo local: nenhuma API, conta ou dado do catálogo é acessado. */
(() => {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const board = $('board');
  const objects = [
    ['🎒', 'Mochila'], ['🔑', 'Chave'], ['🎧', 'Fone'], ['☂️', 'Guarda-chuva'],
    ['📓', 'Caderno'], ['👓', 'Óculos'], ['🧸', 'Ursinho'], ['⌚', 'Relógio'],
    ['🧢', 'Boné'], ['🎮', 'Controle'], ['🧣', 'Cachecol'], ['🧤', 'Luva'],
    ['📱', 'Celular'], ['✏️', 'Lápis'], ['🪪', 'Carteirinha'], ['📷', 'Câmera']
  ];
  const recordKey = 'etec-operacao-achados-recorde-v1';
  let best = 0;
  try {
    const value = Number(localStorage.getItem(recordKey));
    if (Number.isSafeInteger(value) && value > 0 && value <= 100000000) best = value;
  } catch (_) { /* Armazenamento bloqueado não impede uma partida. */ }
  let mode = 'ready', level = 1, score = 0, pairs = 0, pairCount = 6;
  let hints = 2, streak = 0, selected = [], locked = false;
  let remaining = 75000, deadline = 0, ticker = null, focusIndex = 0;
  const pending = new Set();
  const format = new Intl.NumberFormat('pt-BR');

  function later(fn, ms) {
    const id = setTimeout(() => { pending.delete(id); fn(); }, ms);
    pending.add(id);
  }
  function clearPending() {
    pending.forEach(clearTimeout);
    pending.clear();
    $('combo').hidden = true;
  }
  function saveBest() {
    if (score <= best) return;
    best = score;
    try { localStorage.setItem(recordKey, String(best)); } catch (_) {}
    $('best').replaceChildren(document.createTextNode(format.format(best) + ' '));
    const small = document.createElement('small');
    small.textContent = 'pontos';
    $('best').append(small);
  }
  function renderBest() {
    $('best').firstChild.textContent = format.format(best) + ' ';
  }
  function shuffled(values) {
    const items = values.slice();
    for (let i = items.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [items[i], items[j]] = [items[j], items[i]];
    }
    return items;
  }
  function cards() { return Array.from(board.querySelectorAll('.card')); }
  function controls() {
    $('pause').disabled = mode !== 'playing';
    $('hint').disabled = mode !== 'playing' || locked || hints === 0 || selected.length > 0;
    $('hints').textContent = hints;
  }
  function hud() {
    $('level').textContent = String(level).padStart(2, '0');
    $('score').textContent = format.format(score);
    $('pairs').replaceChildren(document.createTextNode(String(pairs)));
    const total = document.createElement('span');
    total.textContent = ' / ' + pairCount;
    $('pairs').append(total);
    controls();
    showTime();
  }
  function showTime() {
    const secs = Math.max(0, Math.ceil(remaining / 1000));
    $('time').textContent = Math.floor(secs / 60) + ':' + String(secs % 60).padStart(2, '0');
    $('timer-box').classList.toggle('urgent', secs <= 15);
  }
  function tick() {
    if (mode !== 'playing') return;
    remaining = Math.max(0, deadline - performance.now());
    showTime();
    if (remaining === 0) finish(false);
  }
  function stopClock() { clearInterval(ticker); ticker = null; }
  function runClock() {
    stopClock();
    deadline = performance.now() + remaining;
    ticker = setInterval(tick, 150);
  }
  function feedback(text) { $('game-feedback').textContent = text; }
  function overlay(kicker, title, description, action, note) {
    board.inert = true;
    $('overlay-kicker').textContent = kicker;
    $('overlay-title').textContent = title;
    $('overlay-description').textContent = description;
    $('play').replaceChildren(document.createTextNode(action + ' '));
    const arrow = document.createElement('span');
    arrow.setAttribute('aria-hidden', 'true'); arrow.textContent = '→';
    $('play').append(arrow);
    $('overlay-note').textContent = note;
    $('overlay').hidden = false;
    $('play').focus({ preventScroll: true });
  }
  function setTab(index, focus = true) {
    const all = cards();
    const target = all[index];
    if (!target || target.disabled) return;
    all.forEach((card, i) => { card.tabIndex = i === index ? 0 : -1; });
    focusIndex = index;
    if (focus) target.focus({ preventScroll: true });
  }
  function createBoard() {
    const pool = shuffled(objects).slice(0, pairCount);
    const deck = shuffled(pool.flatMap(([icon, name], id) => [
      { icon, name, id }, { icon, name, id }
    ]));
    board.replaceChildren();
    board.dataset.size = deck.length;
    deck.forEach((item, i) => {
      const button = document.createElement('button');
      button.type = 'button'; button.className = 'card'; button.tabIndex = i === 0 ? 0 : -1;
      button.dataset.pair = item.id;
      button.dataset.name = item.name;
      button.setAttribute('aria-label', `Carta ${i + 1}, virada para baixo`);
      button.setAttribute('aria-pressed', 'false');
      const inner = document.createElement('span'); inner.className = 'card-inner';
      inner.setAttribute('aria-hidden', 'true');
      const back = document.createElement('span'); back.className = 'card-back';
      const symbol = document.createElement('span'); symbol.textContent = '⌕';
      const brand = document.createElement('small'); brand.textContent = 'ETEC';
      back.append(symbol, brand);
      const front = document.createElement('span'); front.className = 'card-front';
      const icon = document.createElement('span'); icon.className = 'object-icon'; icon.textContent = item.icon;
      const name = document.createElement('span'); name.className = 'object-name'; name.textContent = item.name;
      front.append(icon, name); inner.append(back, front); button.append(inner);
      button.addEventListener('click', () => flip(button, i));
      board.append(button);
    });
    focusIndex = 0;
  }
  function reveal(card, open) {
    card.classList.toggle('revealed', open);
    card.setAttribute('aria-pressed', String(open));
    const number = cards().indexOf(card) + 1;
    card.setAttribute('aria-label', open ? `Carta ${number}: ${card.dataset.name}` : `Carta ${number}, virada para baixo`);
  }
  function resetTurn() {
    clearPending();
    cards().filter(card => !card.classList.contains('matched')).forEach(card => reveal(card, false));
    selected = []; locked = false;
  }
  function begin(nextLevel = false) {
    clearPending(); stopClock();
    if (nextLevel) level++;
    else { level = 1; score = 0; }
    pairCount = Math.min(10, 6 + (level - 1) * 2);
    remaining = (75 + (pairCount - 6) * 5) * 1000;
    pairs = 0; hints = 2; streak = 0; selected = []; locked = false;
    mode = 'playing'; createBoard(); board.inert = false; $('overlay').hidden = true;
    feedback('Encontre dois objetos iguais.');
    hud(); runClock(); setTab(0);
  }
  function finish(won) {
    if (mode !== 'playing') return;
    stopClock(); resetTurn(); mode = won ? 'won' : 'lost';
    const bonus = won ? Math.ceil(remaining / 1000) * 5 : 0;
    score += bonus; saveBest(); hud();
    if (won) {
      feedback(`Fase ${level} concluída!`);
      overlay('SALA ORGANIZADA / MISSÃO CUMPRIDA', 'Tudo de volta ao seu lugar!',
        `Você encontrou os ${pairCount} pares e ganhou mais ${format.format(bonus)} pontos pelo tempo restante. A próxima sala já está esperando.`,
        'Próxima fase', `${format.format(score)} pontos · Próxima sala: ${Math.min(10, pairCount + 2)} pares`);
    } else {
      feedback('O tempo acabou. Que tal outra missão?');
      overlay('FIM DA MISSÃO / VALE MAIS UMA TENTATIVA', 'Quase lá, detetive!',
        `Você chegou à fase ${level} e somou ${format.format(score)} pontos. Cada partida embaralha os objetos: uma nova chance de superar seu recorde.`,
        'Jogar novamente', `Recorde neste navegador: ${format.format(best)} pontos`);
    }
  }
  function flip(card, index) {
    if (mode !== 'playing' || locked || card.disabled || selected.includes(card)) return;
    tick(); if (mode !== 'playing') return;
    setTab(index, false); reveal(card, true); selected.push(card); controls();
    if (selected.length < 2) { feedback(`${card.dataset.name} revelado. Onde está o par?`); return; }
    locked = true; controls();
    const [first, second] = selected;
    if (first.dataset.pair === second.dataset.pair) {
      const hadBoardFocus = board.contains(document.activeElement);
      pairs++; streak++;
      const multiplier = Math.min(3, streak);
      score += 100 * multiplier;
      remaining += 5000; deadline += 5000;
      [first, second].forEach(c => {
        c.classList.add('matched'); c.disabled = true; c.tabIndex = -1;
        c.setAttribute('aria-label', `${c.dataset.name}: par encontrado`);
      });
      selected = []; locked = false; saveBest(); hud();
      feedback(`${first.dataset.name}: par encontrado! +${100 * multiplier} pontos e +5 segundos.`);
      const next = cards().findIndex(c => !c.disabled);
      if (next >= 0) setTab(next, hadBoardFocus);
      if (pairs === pairCount) { finish(true); return; }
      if (multiplier > 1) {
        $('combo').textContent = `COMBO ${multiplier}× · +${100 * multiplier}`;
        $('combo').hidden = false;
        later(() => { $('combo').hidden = true; }, 850);
      }
    } else {
      streak = 0; feedback('Ainda não! Guarde os lugares na memória.');
      later(() => {
        [first, second].forEach(c => reveal(c, false));
        selected = []; locked = false; controls();
        feedback('Escolha mais dois objetos.');
      }, 950);
    }
  }
  function pause() {
    if (mode !== 'playing') return;
    tick(); if (mode !== 'playing') return;
    stopClock(); resetTurn(); mode = 'paused'; controls();
    feedback('Missão pausada. Seu tempo está guardado.');
    overlay('UMA PAUSA PARA RESPIRAR', 'Os objetos podem esperar.',
      'Seu tempo e seus pontos estão guardados nesta partida. Continue quando estiver pronto.',
      'Continuar missão', `Fase ${level} · ${pairs} de ${pairCount} pares encontrados`);
  }
  $('play').addEventListener('click', () => {
    if (mode === 'paused') {
      mode = 'playing'; $('overlay').hidden = true; board.inert = false;
      controls(); runClock(); setTab(focusIndex); feedback('Missão retomada. Vamos achar os pares!');
    } else { begin(mode === 'won'); }
  });
  $('pause').addEventListener('click', pause);
  $('hint').addEventListener('click', () => {
    if (mode !== 'playing' || locked || selected.length || hints < 1) return;
    tick(); if (mode !== 'playing') return;
    hints--; streak = 0; locked = true; controls();
    const hidden = cards().filter(c => !c.disabled);
    hidden.forEach(c => reveal(c, true));
    feedback('Olhe bem! Os objetos aparecem por 1,5 segundo.');
    later(() => {
      hidden.forEach(c => reveal(c, false));
      locked = false; controls(); feedback('Agora é com a sua memória.');
    }, 1500);
  });
  board.addEventListener('keydown', (event) => {
    if (mode !== 'playing') return;
    const step = { ArrowRight: 1, ArrowLeft: -1, ArrowDown: 4, ArrowUp: -4 }[event.key];
    if (!step) return;
    event.preventDefault();
    const all = cards();
    let index = all.indexOf(document.activeElement);
    for (let i = 0; i < all.length; i++) {
      index = (index + step + all.length) % all.length;
      if (!all[index].disabled) { setTab(index); return; }
    }
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && mode === 'playing') { event.preventDefault(); pause(); }
  });
  document.addEventListener('visibilitychange', () => { if (document.hidden) pause(); });
  window.addEventListener('pagehide', pause);
  // Sem cronômetro ou foco automático antes de a pessoa escolher jogar.
  renderBest(); createBoard(); hud();
})();
