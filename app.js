(function () {
  let state = null;
  let language = 'pt';
  const el = id => document.getElementById(id);
  const copy = {
    pt: { overview:'Visão geral', spools:'Bobinas CFS', history:'Histórico', printer:'Painel da impressora', subtitle:'O estado real das quatro posições do CFS, sem inventar bobinas.', refresh:'↻ Atualizar dados', cfs:'Bobinas no CFS', auto:'4 slots · leitura automática', hist:'Histórico de consumo', project:'Projeto ao vivo', noProject:'Sem projeto', noPrint:'Nenhuma impressão ativa', synced:'Sincronizado', rest:'Restam:', noSpool:'Sem bobina detectada', confirmed:'Confirmado pelo histórico de impressões', cfsDetected:'Detectado/calculado pelo CFS', total:'g de consumo confirmado' },
    en: { overview:'Overview', spools:'CFS spools', history:'History', printer:'Printer dashboard', subtitle:'The real state of the four CFS positions, without invented stock.', refresh:'↻ Refresh data', cfs:'CFS spools', auto:'4 slots · automatic reading', hist:'Consumption history', project:'Live project', noProject:'No project', noPrint:'No active print', synced:'Synced', rest:'Remaining:', noSpool:'No spool detected', confirmed:'Confirmed by print history', cfsDetected:'Detected/calculated by CFS', total:'g confirmed consumption' }
  };
  const t = key => copy[language][key] || key;
  function setupLanguage() {
    const header = document.querySelector('.topbar');
    if (!header || document.getElementById('lang-toggle')) return;
    const actions = document.createElement('div'); actions.className = 'top-actions';
    const toggle = document.createElement('button'); toggle.id='lang-toggle'; toggle.className='lang-toggle'; toggle.type='button'; toggle.textContent='EN';
    const sync = el('sync'); header.appendChild(actions); actions.append(toggle); actions.append(sync);
    toggle.addEventListener('click', () => { language = language === 'pt' ? 'en' : 'pt'; toggle.textContent = language === 'pt' ? 'EN' : 'PT'; document.documentElement.lang = language === 'pt' ? 'pt-PT' : 'en'; renderStatic(); render(); });
  }
  function renderStatic() {
    const set = (selector, text) => { const node = document.querySelector(selector); if (node) node.textContent = text; };
    document.querySelectorAll('.nav span').forEach((n,i) => n.textContent = [t('overview'),t('spools'),t('history')][i]);
    set('.eyebrow', t('printer')); set('.topbar p', t('subtitle')); set('#sync', t('refresh')); const heads = document.querySelectorAll('.section-head h2'); if (heads[0]) heads[0].textContent=t('cfs'); if (heads[1]) heads[1].textContent=t('hist'); const legends=document.querySelectorAll('.section-head .legend'); if (legends[0]) legends[0].textContent=t('auto'); const note=document.querySelector('.note'); if(note) note.textContent=language==='pt'?'O saldo mostrado é “restam”. O histórico conserva o nome, a cor, o estado e o consumo de cada envio registado pela K2.':'The displayed balance is “remaining”. History keeps the file name, color, status, and consumption for every K2 job.';
  }
  const colorLabel = code => code && code !== '-1' ? `Cor CFS #${String(code).replace('#','')}` : 'Sem cor detectada';
  function render() {
    if (!state) return;
    const slots = state.cfs || [];
    el('cfs').innerHTML = slots.map(slot => {
      const source = slot.source === 'histórico de impressões'
        ? t('confirmed')
        : (slot.gramsEstimated ? (language === 'pt' ? 'Detectado pelo CFS · peso não informado' : 'Detected by CFS · weight not reported') : t('cfsDetected'));
      const title = slot.loaded ? (slot.color || 'Cor não identificada') : 'Vazio';
      const filament = slot.color === 'black' ? '#24272b' : slot.color === 'white' ? '#e8e4d8' : slot.color === 'gray' ? '#92979d' : slot.color === 'green' ? '#62d38b' : '#8b8b84';
      const imageFilter = slot.color === 'gray' ? 'grayscale(1) brightness(.82)' : slot.color === 'white' ? 'grayscale(1) brightness(1.7)' : slot.color === 'green' ? 'hue-rotate(-60deg) saturate(1.1)' : slot.color === 'black' ? 'grayscale(1) brightness(.32)' : 'none';
      const pct = slot.grams == null ? 0 : Math.max(0, Math.min(100, Number(slot.grams) / 10));
      return `<article class="spool" style="--fill:${slot.loaded ? filament : '#343a42'};--pct:${pct}%"><div class="spool-top"><span class="slot">Slot ${slot.id}</span><span class="state-dot ${slot.loaded ? 'on' : ''}"></span></div><h3>${title}</h3><div class="bar" aria-hidden="true"><i></i></div><div class="spool-visual" style="--img-filter:${imageFilter}" aria-hidden="true"><img src="assets/spool-3d.png" alt="${language === 'pt' ? 'Bobina tridimensional de' : '3D spool of'} ${title}"></div><div class="weight"><strong>${slot.grams == null ? '—' : `${Number(slot.grams).toFixed(1)} g`}</strong><span>${slot.loaded ? `${t('rest')} ${source}` : t('noSpool')}</span></div></article>`;
    }).join('');
    const p = state.project || {}, project = el('project');
    if (!p.loaded) {
      project.className = 'project idle';
      project.innerHTML = `<div><h2>${t('project')}</h2><p>${p.connected ? (language === 'pt' ? 'MCP conectado, mas nenhum projeto está carregado.' : 'MCP connected, but no project is loaded.') : (language === 'pt' ? 'Abra o Creality/MCP para disponibilizar a sessão atual.' : 'Open Creality/MCP to make the current session available.')}</p></div><strong>${t('noProject')}</strong>`;
    } else if (p.comparison && p.comparison.canPrint) {
      project.className = 'project good';
      project.innerHTML = `<div><h2>${p.data.name}</h2><p>${p.data.totalGrams.toFixed(2)} ${language === 'pt' ? 'g previstos · todos os materiais disponíveis' : 'g estimated · all materials available'}</p></div><strong>${language === 'pt' ? 'PODE IMPRIMIR' : 'READY TO PRINT'}</strong>`;
    } else if (p.loaded && p.data && (!p.comparison || !Object.keys(p.data.requirements || {}).length)) {
      const colors = (p.data.colors || []).join(', ') || 'cor não informada';
      project.className = 'project idle';
      project.innerHTML = `<div><h2>${p.data.name}</h2><p>${language === 'pt' ? 'Projeto carregado · filamento detectado' : 'Project loaded · detected filament'}: ${colors}. ${language === 'pt' ? 'Fatie para obter o consumo em gramas.' : 'Slice it to calculate grams.'}</p></div><strong>${language === 'pt' ? 'PROJETO CARREGADO' : 'PROJECT LOADED'}</strong>`;
    } else {
      const shortages = (p.comparison?.shortages || []).map(s => `${s.color}: faltam ${s.missing.toFixed(1)} g`).join(' · ');
      project.className = 'project bad';
      project.innerHTML = `<div><h2>${p.data?.name || (language === 'pt' ? 'Projeto atual' : 'Current project')}</h2><p>${shortages || (language === 'pt' ? 'O MCP não devolveu o consumo por cor.' : 'MCP did not return consumption by color.')}</p></div><strong>${shortages ? (language === 'pt' ? 'NÃO PODE' : 'NOT ENOUGH') : (language === 'pt' ? 'AGUARDANDO DADOS' : 'WAITING FOR DATA')}</strong>`;
    }
    if (state.pending) {
      const q = state.pending;
      el('live').className = 'live';
      el('live').innerHTML = `<div><h2>Em impressão · ${q.filename}</h2><p>${Number(q.usedSoFarGrams||0).toFixed(1)} g extrudidos · só desconta quando concluir</p></div><strong>${Number(q.expectedGrams||0).toFixed(2)} g</strong>`;
    } else {
      el('live').className = 'live idle';
      el('live').innerHTML = `<div><h2>${t('noPrint')}</h2><p>${language === 'pt' ? 'Estado lido automaticamente da K2.' : 'State read automatically from K2.'}</p></div><strong>${t('synced')}</strong>`;
    }
    const jobs = state.jobs || [];
    el('history').innerHTML = jobs.length ? jobs.map(j => `<div class="job"><span>${j.filename}</span><span>${j.color || (language === 'pt' ? 'Cor não identificada' : 'Color not identified')} · ${j.status}</span><strong class="${j.counted ? 'ok' : ''}">${j.counted ? '−' : ''}${Number(j.grams || 0).toFixed(2)} g</strong></div>`).join('') : `<p class="note">${language === 'pt' ? 'Nenhum registro de impressão.' : 'No print records.'}</p>`;
    const counted = jobs.filter(j => j.counted);
    el('spent-total').textContent = `${counted.reduce((sum, j) => sum + Number(j.grams || 0), 0).toFixed(1)} ${t('total')}`;
  }
  async function load(url='/api/state', options) {
    try { const response = await fetch(url, options); state = await response.json(); render(); }
    catch { el('project').innerHTML = '<div><h2>Servidor desligado</h2><p>Abra ABRIR-FILAMENTOS.cmd.</p></div>'; }
  }
  setupLanguage(); renderStatic(); el('sync').addEventListener('click', async () => { await load('/api/sync', {method:'POST'}); });
  load(); setInterval(() => load(), 5000);
})();

