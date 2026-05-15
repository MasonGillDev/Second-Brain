// ── CTA Line Metadata ──────────────────────────────────────────────────────────
const LINE_META = {
  Red:  { label: 'Red',    color: '#c60c30', text: '#fff' },
  Blue: { label: 'Blue',   color: '#00a1de', text: '#fff' },
  Brn:  { label: 'Brown',  color: '#62361b', text: '#fff' },
  G:    { label: 'Green',  color: '#009b3a', text: '#fff' },
  Org:  { label: 'Orange', color: '#f9461c', text: '#fff' },
  Pink: { label: 'Pink',   color: '#e27ea6', text: '#fff' },
  P:    { label: 'Purple', color: '#522398', text: '#fff' },
  Y:    { label: 'Yellow', color: '#f9e300', text: '#222' },
};

// Direction code → human label + SVG arrow
const DIRECTION = {
  '1': { label: 'N / Inbound',  arrow: '↑' },
  '5': { label: 'S / Outbound', arrow: '↓' },
};

// ── Stations grouped by line ───────────────────────────────────────────────────
const STATIONS = {
  Red: [
    { name: 'Howard',            mapid: '40900' },
    { name: 'Jarvis',            mapid: '41190' },
    { name: 'Morse',             mapid: '40100' },
    { name: 'Loyola',            mapid: '41300' },
    { name: 'Granville',         mapid: '40760' },
    { name: 'Thorndale',         mapid: '40880' },
    { name: 'Bryn Mawr',         mapid: '41380' },
    { name: 'Berwyn',            mapid: '40340' },
    { name: 'Argyle',            mapid: '41200' },
    { name: 'Lawrence',          mapid: '40770' },
    { name: 'Wilson',            mapid: '40540' },
    { name: 'Sheridan',          mapid: '40080' },
    { name: 'Addison',           mapid: '41420' },
    { name: 'Belmont',           mapid: '41320' },
    { name: 'Fullerton',         mapid: '41220' },
    { name: 'North/Clybourn',    mapid: '40650' },
    { name: 'Clark/Division',    mapid: '40630' },
    { name: 'Chicago',           mapid: '41450' },
    { name: 'Grand',             mapid: '40490' },
    { name: 'Lake',              mapid: '41660' },
    { name: 'Monroe',            mapid: '41090' },
    { name: 'Jackson',           mapid: '40560' },
    { name: 'Harrison',          mapid: '41490' },
    { name: 'Cermak-Chinatown',  mapid: '41000' },
    { name: 'Sox-35th',          mapid: '40190' },
    { name: '47th',              mapid: '41230' },
    { name: 'Garfield',          mapid: '41170' },
    { name: '63rd',              mapid: '40910' },
    { name: '69th',              mapid: '40990' },
    { name: '79th',              mapid: '40240' },
    { name: '87th',              mapid: '41430' },
    { name: '95th/Dan Ryan',     mapid: '40450' },
  ],
  Blue: [
    { name: "O'Hare",                  mapid: '40890' },
    { name: 'Rosemont',                mapid: '40820' },
    { name: 'Cumberland',              mapid: '40230' },
    { name: "Harlem (O'Hare)",         mapid: '40750' },
    { name: 'Jefferson Park',          mapid: '41280' },
    { name: 'Montrose',                mapid: '41060' },
    { name: 'Irving Park',             mapid: '40090' },
    { name: 'Addison',                 mapid: '41240' },
    { name: 'Belmont',                 mapid: '40060' },
    { name: 'Logan Square',            mapid: '41020' },
    { name: 'California',              mapid: '40570' },
    { name: "Western (O'Hare)",        mapid: '40670' },
    { name: 'Damen',                   mapid: '40590' },
    { name: 'Division',                mapid: '40320' },
    { name: 'Chicago',                 mapid: '41410' },
    { name: 'Grand',                   mapid: '40490' },
    { name: 'Clark/Lake',              mapid: '40380' },
    { name: 'Washington',              mapid: '40370' },
    { name: 'Monroe',                  mapid: '40790' },
    { name: 'Jackson',                 mapid: '40070' },
    { name: 'LaSalle',                 mapid: '41340' },
    { name: 'Clinton',                 mapid: '40430' },
    { name: 'UIC-Halsted',             mapid: '40350' },
    { name: 'Racine',                  mapid: '40470' },
    { name: 'Illinois Medical District', mapid: '40810' },
    { name: 'Western (Forest Park)',   mapid: '40220' },
    { name: 'Kedzie-Homan',            mapid: '40250' },
    { name: 'Pulaski',                 mapid: '40920' },
    { name: 'Cicero',                  mapid: '40970' },
    { name: 'Austin',                  mapid: '40010' },
    { name: 'Oak Park',                mapid: '40180' },
    { name: 'Harlem (Forest Park)',    mapid: '40980' },
    { name: 'Forest Park',             mapid: '40390' },
  ],
  Brn: [
    { name: 'Kimball',           mapid: '41290' },
    { name: 'Kedzie',            mapid: '41180' },
    { name: 'Francisco',         mapid: '40870' },
    { name: 'Rockwell',          mapid: '41010' },
    { name: 'Western',           mapid: '41480' },
    { name: 'Damen',             mapid: '40090' },
    { name: 'Montrose',          mapid: '41500' },
    { name: 'Irving Park',       mapid: '41460' },
    { name: 'Addison',           mapid: '41440' },
    { name: 'Paulina',           mapid: '41310' },
    { name: 'Southport',         mapid: '40360' },
    { name: 'Belmont',           mapid: '41320' },
    { name: 'Fullerton',         mapid: '41220' },
    { name: 'Wellington',        mapid: '41210' },
    { name: 'Diversey',          mapid: '40530' },
    { name: 'Armitage',          mapid: '40660' },
    { name: 'Sedgwick',          mapid: '40400' },
    { name: 'Chicago',           mapid: '40710' },
    { name: 'Merchandise Mart',  mapid: '40460' },
    { name: 'Washington/Wells',  mapid: '40730' },
    { name: 'Quincy',            mapid: '40040' },
    { name: 'LaSalle/Van Buren', mapid: '40160' },
    { name: 'Harold Washington Library', mapid: '40850' },
    { name: 'Adams/Wabash',      mapid: '40680' },
    { name: 'Washington/Wabash', mapid: '41700' },
    { name: 'Randolph/Wabash',   mapid: '40200' },
    { name: 'State/Lake',        mapid: '40260' },
    { name: 'Clark/Lake',        mapid: '40380' },
  ],
  G: [
    { name: 'Harlem/Lake',       mapid: '40020' },
    { name: 'Oak Park',          mapid: '41350' },
    { name: 'Ridgeland',         mapid: '40610' },
    { name: 'Austin',            mapid: '41260' },
    { name: 'Central',           mapid: '40280' },
    { name: 'Laramie',           mapid: '40700' },
    { name: 'Cicero',            mapid: '40480' },
    { name: 'Pulaski',           mapid: '40030' },
    { name: 'Conservatory',      mapid: '41670' },
    { name: 'Kedzie',            mapid: '41070' },
    { name: 'California',        mapid: '41360' },
    { name: 'Ashland',           mapid: '40170' },
    { name: 'Morgan',            mapid: '41510' },
    { name: 'Clinton',           mapid: '41160' },
    { name: 'Clark/Lake',        mapid: '40380' },
    { name: 'State/Lake',        mapid: '40260' },
    { name: 'Randolph/Wabash',   mapid: '40200' },
    { name: 'Adams/Wabash',      mapid: '40680' },
    { name: 'Roosevelt',         mapid: '41400' },
    { name: '35th-Bronzeville',  mapid: '41120' },
    { name: 'Indiana',           mapid: '40300' },
    { name: '43rd',              mapid: '41270' },
    { name: '47th',              mapid: '41080' },
    { name: '51st',              mapid: '40130' },
    { name: 'Garfield',          mapid: '40510' },
    { name: 'King Drive',        mapid: '41140' },
    { name: 'Cottage Grove',     mapid: '40720' },
  ],
  Org: [
    { name: 'Midway',            mapid: '40930' },
    { name: 'Kedzie',            mapid: '41150' },
    { name: 'Western',           mapid: '40310' },
    { name: '35th/Archer',       mapid: '40120' },
    { name: 'Ashland',           mapid: '41060' },
    { name: 'Halsted',           mapid: '41130' },
    { name: 'Roosevelt',         mapid: '41400' },
    { name: 'Harold Washington Library', mapid: '40850' },
    { name: 'LaSalle/Van Buren', mapid: '40160' },
    { name: 'Quincy',            mapid: '40040' },
    { name: 'Washington/Wells',  mapid: '40730' },
    { name: 'Clark/Lake',        mapid: '40380' },
  ],
  Pink: [
    { name: '54th/Cermak',       mapid: '40580' },
    { name: 'Cicero',            mapid: '40420' },
    { name: 'Kostner',           mapid: '41030' },
    { name: 'Pulaski',           mapid: '40650' },
    { name: 'Central Park',      mapid: '40780' },
    { name: 'Kedzie',            mapid: '41040' },
    { name: 'California',        mapid: '40440' },
    { name: 'Western',           mapid: '40740' },
    { name: 'Damen',             mapid: '40210' },
    { name: '18th',              mapid: '40830' },
    { name: 'Polk',              mapid: '41030' },
    { name: 'Ashland',           mapid: '40170' },
    { name: 'Morgan',            mapid: '41510' },
    { name: 'Clinton',           mapid: '41160' },
    { name: 'Clark/Lake',        mapid: '40380' },
    { name: 'State/Lake',        mapid: '40260' },
    { name: 'Randolph/Wabash',   mapid: '40200' },
    { name: 'Adams/Wabash',      mapid: '40680' },
    { name: 'Roosevelt',         mapid: '41400' },
    { name: 'Harold Washington Library', mapid: '40850' },
    { name: 'LaSalle/Van Buren', mapid: '40160' },
    { name: 'Quincy',            mapid: '40040' },
    { name: 'Washington/Wells',  mapid: '40730' },
  ],
  P: [
    { name: 'Linden',            mapid: '41680' },
    { name: 'Central',           mapid: '41250' },
    { name: 'Noyes',             mapid: '40400' },
    { name: 'Foster',            mapid: '40520' },
    { name: 'Davis',             mapid: '40050' },
    { name: 'Dempster',          mapid: '40690' },
    { name: 'Main',              mapid: '40270' },
    { name: 'South Blvd',        mapid: '40840' },
    { name: 'Howard',            mapid: '40900' },
    { name: 'Wilson',            mapid: '40540' },
    { name: 'Belmont',           mapid: '41320' },
    { name: 'Fullerton',         mapid: '41220' },
    { name: 'Merchandise Mart',  mapid: '40460' },
    { name: 'Clark/Lake',        mapid: '40380' },
    { name: 'State/Lake',        mapid: '40260' },
    { name: 'Randolph/Wabash',   mapid: '40200' },
    { name: 'Adams/Wabash',      mapid: '40680' },
    { name: 'Roosevelt',         mapid: '41400' },
    { name: 'Harold Washington Library', mapid: '40850' },
    { name: 'LaSalle/Van Buren', mapid: '40160' },
    { name: 'Quincy',            mapid: '40040' },
    { name: 'Washington/Wells',  mapid: '40730' },
  ],
  Y: [
    { name: 'Dempster-Skokie',   mapid: '40140' },
    { name: 'Oakton-Skokie',     mapid: '41680' },
    { name: 'Howard',            mapid: '40900' },
  ],
};

// ── Favorite stations (highlighted + sorted to top) ──────────────────────────
const FAVORITE_MAPIDS = new Set([
  '41420', // Addison (Red)
  '41320', // Belmont (Red/Brown/Purple)
  '41240', // Addison (Blue)
  '40060', // Belmont (Blue)
  '41440', // Addison (Brown)
]);

// ── State ──────────────────────────────────────────────────────────────────────
let selectedLine = 'Red';
let countdownTimer = null;
let refreshCountdown = 30;
let isFetching = false;

// ── DOM refs ──────────────────────────────────────────────────────────────────
const refreshBtn     = document.getElementById('refresh-btn');
const themeBtn       = document.getElementById('theme-btn');
const themeDark      = document.getElementById('theme-icon-dark');
const themeLight     = document.getElementById('theme-icon-light');
const countdownEl    = document.getElementById('countdown');
const lastUpdatedEl  = document.getElementById('last-updated');
const errorBanner    = document.getElementById('error-banner');
const errorMsg       = document.getElementById('error-msg');
const resultsEl      = document.getElementById('results');
const emptyEl        = document.getElementById('empty');
const linePillsEl    = document.getElementById('line-pills');
// ── Theme ─────────────────────────────────────────────────────────────────────
function initTheme() {
  const saved = localStorage.getItem('cta-theme');
  if (saved) applyTheme(saved, false);
}

function applyTheme(theme, save = true) {
  document.documentElement.setAttribute('data-theme', theme);
  if (save) localStorage.setItem('cta-theme', theme);
  const isDark = theme === 'dark';
  themeDark.style.display  = isDark ? 'block' : 'none';
  themeLight.style.display = isDark ? 'none'  : 'block';
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme');
  // If no attr, infer from system
  const isDark = current ? current === 'dark' : window.matchMedia('(prefers-color-scheme: dark)').matches;
  applyTheme(isDark ? 'light' : 'dark');
}

themeBtn.addEventListener('click', toggleTheme);

// Sync icon on load based on system + saved pref
initTheme();
{
  const saved = localStorage.getItem('cta-theme');
  const isDark = saved
    ? saved === 'dark'
    : window.matchMedia('(prefers-color-scheme: dark)').matches;
  themeDark.style.display  = isDark ? 'block' : 'none';
  themeLight.style.display = isDark ? 'none'  : 'block';
}

// ── Pills ─────────────────────────────────────────────────────────────────────
function buildPills() {
  const allPill = makePill('All', { label: 'All Lines', color: '#444455', text: '#fff' });
  linePillsEl.appendChild(allPill);
  for (const [code, meta] of Object.entries(LINE_META)) {
    linePillsEl.appendChild(makePill(code, meta));
  }
}

function makePill(code, meta) {
  const pill = document.createElement('button');
  pill.className = 'pill' + (code === selectedLine ? ' active' : '');
  pill.dataset.line = code;
  pill.textContent = meta.label;
  pill.style.background = meta.color;
  pill.style.color = meta.text;
  pill.setAttribute('role', 'radio');
  pill.setAttribute('aria-checked', code === selectedLine ? 'true' : 'false');
  pill.addEventListener('click', () => {
    selectedLine = code;
    isFirstLoad = true;
    syncPills();
    refresh();
  });
  return pill;
}

function syncPills() {
  document.querySelectorAll('.pill').forEach(p => {
    const active = p.dataset.line === selectedLine;
    p.classList.toggle('active', active);
    p.setAttribute('aria-checked', active ? 'true' : 'false');
  });
}

// ── Skeleton Loading ───────────────────────────────────────────────────────────
function showSkeletons(count = 6) {
  resultsEl.innerHTML = '';
  emptyEl.classList.add('hidden');
  for (let i = 0; i < count; i++) {
    resultsEl.appendChild(makeSkeletonCard());
  }
}

function makeSkeletonCard() {
  const card = document.createElement('div');
  card.className = 'skeleton-card station-card';

  const header = document.createElement('div');
  header.className = 'skeleton-header';
  header.innerHTML = `
    <div class="sk skeleton-bar" style="width:4px;height:24px;border-radius:2px"></div>
    <div class="sk" style="height:14px;width:55%;border-radius:6px"></div>
    <div class="sk" style="height:18px;width:52px;border-radius:999px;margin-left:auto"></div>
  `;
  card.appendChild(header);

  for (let i = 0; i < 3; i++) {
    const row = document.createElement('div');
    row.className = 'skeleton-row';
    row.innerHTML = `
      <div class="sk" style="width:24px;height:24px;border-radius:6px;flex-shrink:0"></div>
      <div style="flex:1;display:flex;flex-direction:column;gap:5px">
        <div class="sk" style="height:12px;width:70%;border-radius:4px"></div>
        <div class="sk" style="height:10px;width:45%;border-radius:4px"></div>
      </div>
      <div class="sk" style="height:22px;width:52px;border-radius:999px"></div>
    `;
    card.appendChild(row);
  }
  return card;
}

// ── Refresh Logic ──────────────────────────────────────────────────────────────
function refresh() {
  if (isFetching) return;
  resetCountdown();
  fetchArrivals();
}

function resetCountdown() {
  clearInterval(countdownTimer);
  refreshCountdown = 30;
  updateCountdown();
  countdownTimer = setInterval(() => {
    refreshCountdown -= 1;
    updateCountdown();
    if (refreshCountdown <= 0) {
      clearInterval(countdownTimer);
      refresh();
    }
  }, 1000);
}

function updateCountdown() {
  countdownEl.textContent = `${refreshCountdown}s`;
}

// ── Fetch ─────────────────────────────────────────────────────────────────────
let isFirstLoad = true;

async function fetchArrivals() {
  isFetching = true;
  if (isFirstLoad) showSkeletons();
  hideError();

  const lines = selectedLine === 'All' ? Object.keys(STATIONS) : [selectedLine];
  const stationSets = lines.flatMap(line => STATIONS[line] || []);

  // Deduplicate by mapid
  const unique = new Map();
  for (const s of stationSets) unique.set(s.mapid, s);
  const stations = [...unique.values()];

  // Limit stations when showing all lines to avoid hammering the API
  const MAX_STATIONS = selectedLine === 'All' ? 12 : stations.length;
  const toFetch = stations.slice(0, MAX_STATIONS);

  // CTA API only accepts one mapid per request — fetch in parallel batches of 6
  const BATCH = 6;

  try {
    const allEtas = [];
    for (let i = 0; i < toFetch.length; i += BATCH) {
      const batch = toFetch.slice(i, i + BATCH);
      const results = await Promise.all(batch.map(async (s) => {
        const res = await fetch(`api/arrivals?mapid=${s.mapid}`);
        const text = await res.text();
        if (!res.ok) return [];
        try { return parseXML(text); } catch { return []; }
      }));
      allEtas.push(...results.flat());
    }

    renderResults(allEtas);
  } catch (err) {
    console.error('[CTA] Fetch error:', err);
    showError(`Could not load arrivals: ${err.message}`);
    renderResults([]);
  } finally {
    isFetching = false;
    isFirstLoad = false;
    const now = new Date();
    lastUpdatedEl.textContent = `Updated ${now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    refreshBtn.classList.add('spinning');
    setTimeout(() => refreshBtn.classList.remove('spinning'), 700);
  }
}

// ── XML Parsing ───────────────────────────────────────────────────────────────
function getText(parent, tag) {
  return parent.querySelector(tag)?.textContent?.trim() ?? '';
}

function parseXML(xmlText) {
  const parser = new DOMParser();
  const doc = parser.parseFromString(xmlText, 'text/xml');
  const parseErr = doc.querySelector('parsererror');
  if (parseErr) throw new Error('XML parse error: ' + parseErr.textContent);
  const errCd = doc.querySelector('errCd');
  if (errCd && errCd.textContent !== '0') {
    const errNm = doc.querySelector('errNm')?.textContent || 'Unknown CTA error';
    throw new Error(errNm);
  }
  return Array.from(doc.querySelectorAll('eta')).map(eta => ({
    staId:  getText(eta, 'staId'),
    staNm:  getText(eta, 'staNm'),
    stpDe:  getText(eta, 'stpDe'),
    rn:     getText(eta, 'rn'),
    rt:     getText(eta, 'rt'),
    destNm: getText(eta, 'destNm'),
    trDr:   getText(eta, 'trDr'),
    arrT:   getText(eta, 'arrT'),
    isApp:  getText(eta, 'isApp'),
    isDly:  getText(eta, 'isDly'),
  }));
}

// ── Render ────────────────────────────────────────────────────────────────────
function renderResults(etas) {
  resultsEl.innerHTML = '';

  const filtered = selectedLine === 'All'
    ? etas
    : etas.filter(e => e.rt === selectedLine);

  if (filtered.length === 0) {
    emptyEl.classList.remove('hidden');
    return;
  }
  emptyEl.classList.add('hidden');

  // Group by station + line
  const byStation = new Map();
  for (const eta of filtered) {
    const key = `${eta.staId}__${eta.rt}`;
    if (!byStation.has(key)) {
      byStation.set(key, { staId: eta.staId, staNm: eta.staNm, rt: eta.rt, etas: [] });
    }
    byStation.get(key).etas.push(eta);
  }

  // Sort: favorites first, then by line, then by station name
  const sorted = [...byStation.values()].sort((a, b) => {
    const aFav = FAVORITE_MAPIDS.has(a.staId);
    const bFav = FAVORITE_MAPIDS.has(b.staId);
    if (aFav !== bFav) return aFav ? -1 : 1;
    if (a.rt !== b.rt) return a.rt.localeCompare(b.rt);
    return a.staNm.localeCompare(b.staNm);
  });

  sorted.forEach((station, i) => {
    const card = makeStationCard(station);
    card.style.animationDelay = `${Math.min(i * 30, 300)}ms`;
    resultsEl.appendChild(card);
  });
}

function makeStationCard({ staId, staNm, rt, etas }) {
  const meta = LINE_META[rt] || { label: rt, color: '#888', text: '#fff' };
  const isFav = FAVORITE_MAPIDS.has(staId);

  const card = document.createElement('div');
  card.className = 'station-card' + (isFav ? ' station-fav' : '');

  // Header
  const header = document.createElement('div');
  header.className = 'station-header';
  header.style.borderLeftColor = meta.color;

  const name = document.createElement('div');
  name.className = 'station-name';
  name.textContent = staNm;

  const badge = document.createElement('span');
  badge.className = 'line-badge';
  badge.textContent = meta.label;
  badge.style.background = meta.color + '22';
  badge.style.color = meta.color;
  badge.style.borderColor = meta.color + '44';

  header.append(name, badge);
  card.appendChild(header);

  // Divider
  const div = document.createElement('div');
  div.className = 'station-divider';
  card.appendChild(div);

  // Trains (up to 4, sorted by arrival time)
  const sorted = [...etas].sort((a, b) => new Date(a.arrT) - new Date(b.arrT));
  const list = document.createElement('ul');
  list.className = 'train-list';

  for (const eta of sorted.slice(0, 4)) {
    list.appendChild(makeTrainRow(eta, meta));
  }
  card.appendChild(list);
  return card;
}

function makeTrainRow(eta, meta) {
  const li = document.createElement('li');
  li.className = 'train-row';

  const mins = minutesUntil(eta.arrT, eta.isApp);
  const isDly = eta.isDly === '1';
  const dir = DIRECTION[eta.trDr] || { arrow: '·' };

  // Direction icon
  const dirIcon = document.createElement('div');
  dirIcon.className = 'train-dir-icon';
  dirIcon.style.background = meta.color + '22';
  dirIcon.style.color = meta.color;
  dirIcon.textContent = dir.arrow;
  dirIcon.title = dir.label || '';

  // Info
  const info = document.createElement('div');
  info.className = 'train-info';

  const dest = document.createElement('div');
  dest.className = 'train-dest';
  dest.textContent = `To ${eta.destNm}`;

  const stopDesc = document.createElement('div');
  stopDesc.className = 'train-stop-desc';
  stopDesc.textContent = eta.stpDe || '';

  info.append(dest, stopDesc);

  // Arrival chip
  const timeDiv = document.createElement('div');
  timeDiv.className = 'train-time';

  const chip = document.createElement('span');
  chip.className = `arrival-chip ${chipClass(mins, isDly)}`;

  if (isDly) {
    chip.textContent = 'Delayed';
  } else if (eta.isApp === '1' || mins <= 0) {
    chip.textContent = 'Due';
  } else {
    chip.textContent = `${mins} min`;
  }

  timeDiv.appendChild(chip);
  li.append(dirIcon, info, timeDiv);
  return li;
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function minutesUntil(arrT, isApp) {
  if (isApp === '1') return 0;
  // CTA format: "20260508 09:06:24" → parse manually
  const [date, time] = arrT.split(' ');
  if (!date || !time) return 0;
  const iso = `${date.slice(0,4)}-${date.slice(4,6)}-${date.slice(6,8)}T${time}`;
  return Math.max(0, Math.round((new Date(iso) - Date.now()) / 60000));
}

function chipClass(mins, isDly) {
  if (isDly)      return 'chip-delayed';
  if (mins <= 1)  return 'chip-due';
  if (mins <= 5)  return 'chip-soon';
  if (mins <= 10) return 'chip-medium';
  return 'chip-far';
}

function showError(msg) {
  errorMsg.textContent = msg;
  errorBanner.classList.remove('hidden');
}

function hideError() {
  errorBanner.classList.add('hidden');
}

// ── Init ──────────────────────────────────────────────────────────────────────
buildPills();
refreshBtn.addEventListener('click', refresh);
refresh();
