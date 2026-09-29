(() => {
  const configuredApi = new URLSearchParams(location.search).get('api');
  if (configuredApi) localStorage.setItem('creator_marketplace_api', configuredApi);
  const API = (configuredApi || localStorage.getItem('creator_marketplace_api') || 'http://localhost:8000').replace(/\/$/, '');
  const state = { view: 'discover', user: null, profile: null, creators: [], creatorDirectory: { page: 1, limit: 24, total: 0, total_pages: 0, niches: [], platforms: [] }, creatorSource: 'marketplace', youtubeResults: [], youtubePageTokens: [null], youtubePage: 0, youtubeQuery: '', campaigns: [], saved: new Set(JSON.parse(localStorage.getItem('saved_creators') || '[]')), filters: { q: '', niche: '', platform: '', sort: 'recommended' }, authMode: 'login', authRole: 'brand', googleClientId: null, searchTimer: null, searchSequence: 0, semanticSearch: false, assistantConversation: [] };
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const esc = (value = '') => String(value).replace(/[&<>"']/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]));
  const number = value => Number(value || 0).toLocaleString('en-US');
  const money = value => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(value || 0);
  const initials = value => String(value || 'C').trim().split(/\s+/).map(part => part[0]).join('').slice(0, 2).toUpperCase();
  const toast = message => { const el = $('#toast'); el.textContent = message; el.classList.add('show'); setTimeout(() => el.classList.remove('show'), 2600); };
  function setTheme(theme) {
    const selected = theme === 'dark' ? 'dark' : 'light';
    document.documentElement.dataset.theme = selected;
    localStorage.setItem('creator_marketplace_theme', selected);
    const toggle = $('#theme-toggle');
    if (toggle) {
      toggle.textContent = selected === 'dark' ? '☀' : '☾';
      toggle.setAttribute('aria-label', `Switch to ${selected === 'dark' ? 'light' : 'dark'} mode`);
      toggle.title = `Switch to ${selected === 'dark' ? 'light' : 'dark'} mode`;
    }
    const themeColor = $('meta[name="theme-color"]');
    if (themeColor) themeColor.content = selected === 'dark' ? '#100e14' : '#faf8f8';
  }
  async function api(path, options = {}) {
    const token = localStorage.getItem('creator_marketplace_token');
    const headers = { ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...(token ? { Authorization: `Bearer ${token}` } : {}), ...options.headers };
    const response = await fetch(`${API}${path}`, { ...options, headers });
    let data; try { data = await response.json(); } catch { data = {}; }
    if (!response.ok) { const error = new Error(data.detail || `Request failed (${response.status})`); error.status = response.status; throw error; }
    return data;
  }
  const accountName = () => state.profile?.company_name || state.profile?.display_name || state.user?.email?.split('@')[0] || 'Guest';
  function updateAccount() { $('#account-name').textContent = accountName(); $('#account-role').textContent = state.user ? (state.user.role === 'brand' ? 'Company workspace' : 'Creator workspace') : 'Guest workspace'; $('#avatar').textContent = initials(accountName()); $('#header-sign-in').hidden = Boolean(state.user); }
  async function initialize() {
    try { state.googleClientId = (await api('/auth/oauth/google/config')).client_id; } catch { state.googleClientId = null; }
    if (localStorage.getItem('creator_marketplace_token')) {
      try { state.user = await api('/auth/me'); await loadProfile(); }
      catch (error) {
        if (error.status === 401) { logout(false); toast('Your session expired. Sign in once to continue.'); }
        else { console.warn('Could not verify the saved session:', error); toast('Could not verify your saved session. Check the API connection and retry.'); }
      }
    }
    updateAccount(); await navigate(location.hash.slice(1) || 'discover');
  }
  async function loadProfile() { try { state.profile = await api(state.user.role === 'brand' ? '/brands/me' : '/creators/me'); } catch (error) { if (!String(error.message).includes('not found')) console.warn(error); state.profile = null; } updateAccount(); }
  async function navigate(view) {
    const creatorRoute = /^creator\/(\d+)$/.exec(view), youtubeRoute = /^youtube\/([A-Za-z0-9_-]{6,})$/.exec(view);
    state.view = creatorRoute || youtubeRoute ? 'creator-detail' : ['discover', 'campaigns', 'partnerships', 'profile'].includes(view) ? view : 'discover';
    state.creatorId = creatorRoute ? Number(creatorRoute[1]) : null;
    state.youtubeChannelId = youtubeRoute?.[1] || null;
    history.replaceState(null, '', `#${creatorRoute || youtubeRoute ? view : state.view}`);
    $$('.nav-item').forEach(button => button.classList.toggle('active', button.dataset.view === state.view));
    const labels = { discover: 'Discover creators', campaigns: 'Campaigns', partnerships: 'Partnerships', profile: 'My profile', 'creator-detail': 'Creator analytics' }; $('#crumb').textContent = labels[state.view];
    if (state.view === 'discover') await renderDiscover(); else if (state.view === 'campaigns') await renderCampaigns(); else if (state.view === 'partnerships') await renderPartnerships(); else if (state.view === 'creator-detail') state.youtubeChannelId ? await renderYouTubeDetails(state.youtubeChannelId) : await renderCreatorDetails(state.creatorId); else await renderProfile();
  }
  function authWall(title = 'Join the marketplace', copy = 'Create a free account to build your profile, manage campaigns, and start making better partnerships.') {
    if (state.user) return `<section class="auth-wall"><div class="empty-illustration">◉</div><h2>${esc(title)}</h2><p>${esc(copy)} You’re signed in as <strong>${esc(state.user.email)}</strong>.</p><button class="button button-dark" data-go="profile">Finish your profile ↗</button></section>`;
    return `<section class="auth-wall"><div class="empty-illustration">✳</div><h2>${esc(title)}</h2><p>${esc(copy)}</p><div class="auth-wall-actions"><button class="button button-dark" data-auth="register" data-auth-role="creator">I’m a creator ↗</button><button class="button button-outline" data-auth="register" data-auth-role="brand">I’m a company ↗</button></div><button class="auth-wall-login" data-auth="login" data-auth-role="brand">Already here? Sign in</button></section>`;
  }
  async function renderDiscover() {
    const page = $('#page'); page.innerHTML = `<div class="loading">Finding your next great collaboration…</div>`;
    try { state.creatorDirectory = await api('/creators/directory?page=1&limit=24'); state.creators = state.creatorDirectory.results; } catch (error) { page.innerHTML = `<div class="heading-row"><div><div class="eyebrow">Creator intelligence</div><h1>Find your next great collab</h1><p class="subhead">A great partnership starts with the right creator.</p></div></div><div class="error-state"><div class="empty-illustration">⌕</div><h2>Couldn’t reach the marketplace</h2><p>${esc(error.message)}. Make sure the API is running at <code>${esc(API)}</code>.</p><button class="button button-outline" id="retry-discover">Try again</button></div>`; $('#retry-discover').onclick = renderDiscover; return; }
    page.innerHTML = `<section class="hero-stage"><div class="hero-copy"><div class="hero-kicker"><i></i> THE CREATOR ECONOMY, IN MOTION</div><h1>Culture moves.<br><span>Find who moves it.</span></h1><p>Creator partnerships, built around the people and ideas your audience already loves.</p><div class="hero-actions"><button class="button button-accent" id="hero-company">Build a campaign <span>↗</span></button><button class="hero-link" id="hero-creator">I’m a creator <span>↗</span></button></div><div class="hero-trust"><div class="avatar-stack"><b>J</b><b>M</b><b>A</b><b>+</b></div><span>Better matches start with real impact</span></div></div><div class="hero-art"><div class="art-glow"></div><div class="art-orbit orbit-one"></div><div class="art-orbit orbit-two"></div><div class="campaign-preview"><div class="preview-top"><span>FOLIO CAMPAIGN / 024</span><span class="preview-live"><i></i> LIVE</span></div><div class="preview-image"><div class="sun-disc"></div><div class="shape-bottle"></div><div class="preview-caption">Make it<br><em>matter.</em></div><span class="preview-chip">NEW DROP · CULTURE IN COLOR</span></div><div class="preview-bottom"><div class="mini-creator"><b>R</b><span><strong>Riya Mehta</strong><small>Beauty · Mumbai</small></span></div><div class="match-score"><strong>96</strong><small>FIT SCORE</small></div></div></div><div class="floating-note note-top"><span>✳</span> Made for your audience</div><div class="floating-note note-bottom"><b>+42%</b><span>engagement lift</span></div><div class="hero-stamp">REAL<br>PEOPLE<br><span>✳</span></div></div><div class="hero-index"><span>01 — DISCOVER</span><span>MAKE BETTER PARTNERSHIPS <b>↗</b></span></div></section><div class="heading-row discovery-heading"><div><div class="eyebrow">Creator intelligence</div><h2>Find your next great collab</h2><p class="subhead">Meet creators who move people, not just numbers.</p></div><div class="heading-actions"><button class="button button-outline" id="saved-filter">♡ Saved creators</button><button class="button button-dark" id="create-campaign-inline">Create campaign ＋</button></div></div><div class="directory-source-switch"><button class="source-tab active" data-creator-source="marketplace">Folio members <span>Joined creators</span></button><button class="source-tab" data-creator-source="youtube">YouTube discovery <span>Live public channels</span></button><small>Public channel stats come directly from YouTube and are not saved as Folio creator accounts.</small></div><div class="search-panel"><label class="search-box"><span>⌕</span><input id="creator-search" type="search" placeholder="Search creators, niches, or locations" value="${esc(state.filters.q)}" /></label><select id="niche-filter"><option value="">All niches</option>${optionsFrom(state.creatorDirectory.niches, state.filters.niche)}</select><select id="platform-filter"><option value="">All platforms</option>${optionsFrom(state.creatorDirectory.platforms, state.filters.platform)}</select><select id="sort-filter"><option value="recommended">Recommended</option><option value="performance">Top performance</option><option value="followers">Most followers</option><option value="engagement">Top engagement</option><option value="name">Name</option></select></div><div class="result-line"><span><strong id="result-count">${state.creatorDirectory.total}</strong> creators in the marketplace</span><span id="directory-status">Browse real creator profiles · metrics shown when available</span></div><div class="creator-grid" id="creator-grid"></div><nav class="pagination" id="creator-pagination" aria-label="Creator pages"></nav><div class="page-footer">Creator quality, measured beyond follower count.</div>`;
    $('.hero-stage').outerHTML = `<section class="portfolio-hero"><div class="portfolio-photo" role="img" aria-label="Editorial portrait in warm natural light"></div><div class="portfolio-shade"></div><div class="portfolio-copy"><div class="portfolio-kicker"><span></span> FOLIO · CREATOR STORIES</div><h1>People make<br><em>the difference.</em></h1><p>Find creators whose point of view gives your next campaign a pulse.</p><div class="portfolio-actions"><button class="button button-accent" id="hero-company">Find your people <span>↗</span></button><button class="portfolio-link" id="hero-creator">Join as a creator <span>↗</span></button></div></div><div class="portfolio-caption"><span>01 / CREATOR PORTRAITS</span><span>REAL PEOPLE. REAL PARTNERSHIPS.</span></div><div class="portfolio-scroll">SCROLL TO DISCOVER <span>↓</span></div></section>`;
    $('#niche-filter').value = state.filters.niche; $('#platform-filter').value = state.filters.platform; $('#sort-filter').value = state.filters.sort;
    $('#creator-search').addEventListener('input', event => { state.filters.q = event.target.value; clearTimeout(state.searchTimer); state.searchTimer = setTimeout(() => state.creatorSource === 'youtube' ? loadYouTubePage(0, true) : loadCreatorDirectory(1), state.creatorSource === 'youtube' ? 650 : 280); });
    $$('[data-creator-source]').forEach(button => button.onclick = () => switchCreatorSource(button.dataset.creatorSource));
    ['niche-filter', 'platform-filter', 'sort-filter'].forEach(id => $(`#${id}`).addEventListener('change', event => { if (id === 'niche-filter') state.filters.niche = event.target.value; if (id === 'platform-filter') state.filters.platform = event.target.value; if (id === 'sort-filter') state.filters.sort = event.target.value; loadCreatorDirectory(1); }));
    $('#saved-filter').onclick = () => { state.filters.savedOnly = !state.filters.savedOnly; $('#saved-filter').classList.toggle('button-lime', state.filters.savedOnly); $('#saved-filter').innerHTML = state.filters.savedOnly ? '♥ Showing saved' : '♡ Saved creators'; loadCreatorDirectory(1); };
    $('#create-campaign-inline').onclick = () => state.user?.role === 'brand' ? openCampaignDialog() : state.user ? toast('This workspace is signed in as a creator. Switch to a company account to create campaigns.') : openAuth('register', 'brand');
    $('#hero-company').onclick = () => state.user?.role === 'brand' ? openCampaignDialog() : state.user ? toast('You’re signed in as a creator. Use a company account to create campaigns.') : openAuth('register', 'brand');
    $('#hero-creator').onclick = () => state.user?.role === 'creator' ? navigate('profile') : state.user ? toast('You’re signed in with a company account.') : openAuth('register', 'creator');
    if (state.creatorSource === 'youtube') switchCreatorSource('youtube'); else renderCreatorCards();
  }
  function switchCreatorSource(source) {
    if (source === 'youtube' && !state.user) { openAuth('login', 'brand'); toast('Sign in to search live YouTube channels'); return; }
    state.creatorSource = source;
    $$('[data-creator-source]').forEach(button => button.classList.toggle('active', button.dataset.creatorSource === source));
    ['niche-filter', 'platform-filter', 'sort-filter'].forEach(id => { $(`#${id}`).hidden = source === 'youtube'; });
    $('#creator-search').placeholder = source === 'youtube' ? 'Search YouTube channels by topic, creator, or keyword' : 'Search creators, niches, or locations';
    $('#saved-filter').hidden = source === 'youtube';
    if (source === 'youtube') {
      $('#directory-status').textContent = 'Search public YouTube channels · add a topic above';
      $('#creator-grid').innerHTML = `<div class="empty-state"><div class="empty-illustration">⌕</div><h2>Search the YouTube creator index</h2><p>Try a topic such as skincare, street food, travel, gaming, or fitness.</p></div>`;
      $('#result-count').textContent = '—'; $('#creator-pagination').innerHTML = '';
      if (state.filters.q.trim().length >= 2) loadYouTubePage(0, true);
    } else loadCreatorDirectory(1);
  }
  async function loadCreatorDirectory(page = state.creatorDirectory.page || 1, initial = true) {
    const sequence = ++state.searchSequence;
    const params = new URLSearchParams({ page, limit: state.creatorDirectory.limit || 24, sort_by: state.filters.sort === 'recommended' ? 'recommended' : state.filters.sort });
    if (state.filters.q.trim()) params.set('q', state.filters.q.trim());
    if (state.filters.niche) params.set('niche', state.filters.niche);
    if (state.filters.platform) params.set('platform', state.filters.platform);
    if (state.filters.savedOnly) { params.set('saved_only', 'true'); [...state.saved].forEach(id => params.append('creator_ids', id)); }
    try {
      const result = await api(`/creators/directory?${params}`);
      if (sequence !== state.searchSequence || !$('#creator-grid')) return;
      state.creatorDirectory = { ...result, limit: result.limit };
      state.creators = result.results;
      renderCreatorCards();
    } catch (error) { if (!initial && sequence === state.searchSequence) toast(`Creator search unavailable: ${error.message}`); }
  }
  async function loadYouTubePage(page = 0, reset = false) {
    const query = state.filters.q.trim();
    if (query.length < 2) { $('#directory-status').textContent = 'Enter at least two characters to search public YouTube channels'; return; }
    if (!state.user) { openAuth('login', 'brand'); return; }
    if (reset || query !== state.youtubeQuery) { state.youtubeQuery = query; state.youtubePageTokens = [null]; page = 0; }
    const token = state.youtubePageTokens[page];
    if (page > 0 && !token) return;
    const sequence = ++state.searchSequence;
    $('#directory-status').textContent = 'Searching YouTube for public channels…';
    $('#creator-grid').innerHTML = `<div class="loading">Finding public creator channels…</div>`;
    try {
      const params = new URLSearchParams({ q: query, limit: 24 }); if (token) params.set('page_token', token);
      const result = await api(`/creators/youtube-discover?${params}`);
      if (sequence !== state.searchSequence || state.creatorSource !== 'youtube') return;
      state.youtubeResults = result.results; state.youtubePage = page;
      if (result.next_page_token) state.youtubePageTokens[page + 1] = result.next_page_token;
      $('#creator-grid').innerHTML = result.results.length ? result.results.map(youtubeCreatorCard).join('') : `<div class="empty-state"><h2>No channels found</h2><p>Try a broader topic or another keyword.</p></div>`;
      $('#result-count').textContent = result.result_count;
      $('#directory-status').textContent = `${result.data_source} · live results for “${query}”`;
      $('#creator-pagination').innerHTML = `<button class="page-button" data-youtube-page="${page - 1}" ${page === 0 ? 'disabled' : ''}>← Previous</button><span>Results page <strong>${page + 1}</strong></span><button class="page-button" data-youtube-page="${page + 1}" ${!result.next_page_token ? 'disabled' : ''}>Next →</button>`;
      $$('[data-youtube-page]').forEach(button => button.addEventListener('click', () => loadYouTubePage(Number(button.dataset.youtubePage))));
      $$('[data-open-youtube]').forEach(button => button.onclick = () => navigate(`youtube/${button.dataset.openYoutube}`));
    } catch (error) {
      if (sequence !== state.searchSequence) return;
      $('#creator-grid').innerHTML = `<div class="error-state"><h2>YouTube discovery isn’t available</h2><p>${esc(error.message)}</p><small>The site owner needs to configure YOUTUBE_API_KEY on the backend.</small></div>`;
      $('#directory-status').textContent = 'YouTube connection unavailable'; $('#creator-pagination').innerHTML = '';
    }
  }
  function youtubeCreatorCard(creator) {
    const audience = creator.subscriber_count_hidden ? 'Hidden by channel owner' : creator.subscriber_count == null ? 'Unavailable' : number(creator.subscriber_count);
    return `<article class="creator-card youtube-creator-card"><div class="youtube-cover">${creator.thumbnail_url ? `<img src="${esc(creator.thumbnail_url)}" alt="" loading="lazy" referrerpolicy="no-referrer" />` : `<span>${esc(initials(creator.title))}</span>`}<span class="youtube-source-label">YOUTUBE · PUBLIC</span></div><div class="creator-body"><div class="name-line"><span class="creator-name">${esc(creator.title)}</span></div><div class="handle">Channel ID · ${esc(creator.channel_id)}${creator.country ? ` · ${esc(creator.country)}` : ''}</div><p class="creator-desc">${esc(creator.description || 'No channel description provided.').slice(0, 220)}</p><div class="card-stats"><div class="stat"><b>${audience}</b><small>Subscribers</small></div><div class="stat"><b>${creator.total_views == null ? '—' : number(creator.total_views)}</b><small>Channel views</small></div><div class="stat"><b>${creator.video_count == null ? '—' : number(creator.video_count)}</b><small>Videos</small></div></div><div class="card-footer"><button class="button button-outline" data-open-youtube="${esc(creator.channel_id)}">View public analytics ↗</button><a class="button button-light" href="${esc(creator.channel_url)}" target="_blank" rel="noopener noreferrer">Open YouTube</a></div></div></article>`;
  }
  function optionsFrom(values, selected) { return [...new Set(values.filter(Boolean))].sort().map(value => `<option ${value === selected ? 'selected' : ''} value="${esc(value)}">${esc(value)}</option>`).join(''); }
  function renderCreatorCards() {
    const creators = state.creators;
    $('#result-count').textContent = state.creatorDirectory.total;
    const first = state.creatorDirectory.total ? (state.creatorDirectory.page - 1) * state.creatorDirectory.limit + 1 : 0;
    const last = Math.min(state.creatorDirectory.page * state.creatorDirectory.limit, state.creatorDirectory.total);
    $('#directory-status').textContent = state.creatorDirectory.total ? `Showing ${first}–${last} · creator profiles with metrics when available` : 'No matching creator profiles';
    $('#creator-grid').innerHTML = creators.length ? creators.map(creatorCard).join('') : `<div class="empty-state"><div class="empty-illustration">⌕</div><h2>No creators found</h2><p>Try adjusting your search or filters, or invite creators to join Folio.</p><button class="button button-outline" id="clear-filters">Clear filters</button></div>`;
    const pageCount = state.creatorDirectory.total_pages;
    $('#creator-pagination').innerHTML = pageCount > 1 ? `<button class="page-button" data-page="${state.creatorDirectory.page - 1}" ${state.creatorDirectory.page <= 1 ? 'disabled' : ''}>← Previous</button><span>Page <strong>${state.creatorDirectory.page}</strong> of ${pageCount}</span><button class="page-button" data-page="${state.creatorDirectory.page + 1}" ${state.creatorDirectory.page >= pageCount ? 'disabled' : ''}>Next →</button>` : '';
    $$('.page-button').forEach(button => button.addEventListener('click', () => loadCreatorDirectory(Number(button.dataset.page))));
    $('#clear-filters')?.addEventListener('click', () => { state.filters = { q: '', niche: '', platform: '', sort: 'recommended' }; state.filters.savedOnly = false; renderDiscover(); });
    $$('.save-button').forEach(button => button.onclick = () => { const id = Number(button.dataset.id); state.saved.has(id) ? state.saved.delete(id) : state.saved.add(id); localStorage.setItem('saved_creators', JSON.stringify([...state.saved])); button.classList.toggle('saved', state.saved.has(id)); button.textContent = state.saved.has(id) ? '♥' : '♡'; if (state.filters.savedOnly) loadCreatorDirectory(state.creatorDirectory.page); });
    $$('.invite-creator').forEach(button => button.onclick = () => state.user?.role === 'brand' ? inviteCreator(Number(button.dataset.id)) : navigate('campaigns'));
    $$('[data-view-creator]').forEach(button => button.onclick = () => navigate(`creator/${button.dataset.viewCreator}`));
  }
  function creatorCard(c) {
    const saved = state.saved.has(c.creator_id), name = c.display_name || c.username, location = [c.city, c.country].filter(Boolean).join(', ') || 'Location not listed';
    const label = c.relevance_score != null ? `Topic match <b>${Number(c.relevance_score).toFixed(0)}%</b>` : `Performance <b>${Number(c.performance_score || 0).toFixed(0)}</b>`;
    const action = state.user?.role === 'brand' ? 'Invite to campaign ↗' : 'See campaigns ↗';
    const hasMetrics = c.has_metrics ?? Boolean(c.average_views || c.engagement_rate || c.performance_score);
    return `<article class="creator-card"><div class="creator-cover"><div class="cover-art"></div><div class="cover-glow"></div><div class="creator-avatar"><div class="portrait">${esc(initials(name))}</div></div><button class="save-button ${saved ? 'saved' : ''}" data-id="${c.creator_id}" aria-label="${saved ? 'Unsave' : 'Save'} creator">${saved ? '♥' : '♡'}</button></div><div class="creator-body"><div class="name-line"><span class="creator-name">${esc(name)}</span></div><div class="handle">Creator #${c.creator_id} · @${esc(c.username)} · ${esc(location)}</div><p class="creator-desc">${esc(c.bio || `${c.niche || 'Creator'} profile${hasMetrics ? ` · ${c.platform || 'Social'} metrics available` : ' · performance data not shared yet'}.`)}</p><div class="tags"><span class="tag">${esc(c.niche || 'Creator')}</span><span class="tag">${esc(c.platform || 'Platform not listed')}</span>${c.country ? `<span class="tag">${esc(c.country)}</span>` : ''}</div><div class="card-stats"><div class="stat"><b>${number(c.followers)}</b><small>Followers${hasMetrics ? '' : ' · profile'}</small></div><div class="stat"><b>${hasMetrics ? number(c.average_views) : '—'}</b><small>Avg. views</small></div><div class="stat"><b class="engagement">${hasMetrics ? `${Number(c.engagement_rate || 0).toFixed(1)}%` : '—'}</b><small>Engagement</small></div></div><div class="card-footer"><button class="button button-outline" data-view-creator="${c.creator_id}">Open profile + analytics ↗</button><button class="button button-light invite-creator" data-id="${c.creator_id}">${action}</button></div></div></article>`;
  }
  function trendChart(snapshots) {
    const values = snapshots.filter(row => row.followers != null).map(row => Number(row.followers));
    if (values.length < 2) return `<div class="analytics-empty">${values.length ? 'Add another dated metric snapshot to see follower growth over time.' : 'No follower history is available for this account yet.'}</div>`;
    const width = 560, height = 150, min = Math.min(...values), max = Math.max(...values), span = max - min || 1;
    const points = values.map((value, index) => `${Math.round(index * width / (values.length - 1))},${Math.round(height - 12 - (value - min) / span * (height - 24))}`).join(' ');
    return `<svg class="creator-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="Follower count trend"><polyline points="${points}" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/><text x="4" y="${height - 1}">${number(min)}</text><text x="${width - 72}" y="${height - 1}">${number(max)}</text></svg>`;
  }
  async function renderCreatorDetails(creatorId) {
    const page = $('#page');
    page.innerHTML = `<div class="loading">Loading creator profile and analytics…</div>`;
    try {
      const data = await api(`/creators/${creatorId}/analytics`);
      const latestAccounts = data.accounts.map(account => {
        const latest = account.latest, yt = latest?.data_source === 'youtube_public';
        const url = /^https?:\/\//i.test(account.profile_url || '') ? esc(account.profile_url) : '';
        return `<article class="creator-account-analytics"><div class="creator-account-head"><div><span class="eyebrow">${esc(account.platform)}</span><h3>@${esc(account.username)}</h3></div>${url ? `<a class="button button-outline" href="${url}" target="_blank" rel="noopener noreferrer">Open social profile ↗</a>` : ''}</div>${latest ? `<div class="analytics-metrics"><div><small>${yt ? 'Subscribers' : 'Followers'}</small><strong>${number(latest.followers)}</strong></div>${yt ? `<div><small>Channel views</small><strong>${number(latest.total_views)}</strong></div><div><small>Videos</small><strong>${number(latest.total_videos)}</strong></div>` : `<div><small>Average views</small><strong>${number(latest.average_views)}</strong></div><div><small>Engagement rate</small><strong>${latest.engagement_rate == null ? '—' : `${Number(latest.engagement_rate).toFixed(1)}%`}</strong></div>`}</div><div class="analytics-chart-head"><strong>${yt ? 'Subscriber history' : 'Follower history'}</strong><small>${latest.metric_date ? `Latest snapshot · ${esc(latest.metric_date)}` : 'Latest available snapshot'}</small></div>${trendChart(account.snapshots)}</div>` : `<div class="analytics-empty">No analytics snapshots yet. The creator can connect an account and add metrics from their profile.</div>`}</article>`;
      }).join('');
      page.innerHTML = `<div class="creator-detail-top"><button class="button button-outline" id="creator-detail-back">← Back to creators</button><span class="eyebrow">CREATOR PROFILE · #${data.creator_id}</span></div><section class="creator-detail-hero"><div class="detail-monogram">${esc(initials(data.display_name || data.username))}</div><div><div class="eyebrow">${esc(data.niche || 'Creator')}</div><h1>${esc(data.display_name || data.username)}</h1><p class="subhead">@${esc(data.username)} · ${esc([data.city, data.country].filter(Boolean).join(', ') || 'Location not listed')}</p><p>${esc(data.bio || 'This creator has not added a bio yet.')}</p></div><button class="button button-dark" id="detail-invite">${state.user?.role === 'brand' ? 'Invite to campaign ↗' : 'Explore campaigns ↗'}</button></section><div class="section-heading"><h2>Account analytics</h2><span class="subhead">Snapshots by connected platform. No estimated figures.</span></div><div class="creator-analytics-list">${latestAccounts || `<div class="analytics-empty">No social accounts or analytics are connected to this creator profile yet.</div>`}</div><p class="analytics-note">YouTube figures are public channel statistics. Engagement and average views appear only when the creator has shared those metrics.</p>`;
      $('#creator-detail-back').onclick = () => navigate('discover');
      $('#detail-invite').onclick = () => state.user?.role === 'brand' ? inviteCreator(Number(data.creator_id)) : state.user ? navigate('campaigns') : openAuth('login', 'brand');
    } catch (error) {
      page.innerHTML = `<div class="error-state"><h2>Creator profile couldn’t load</h2><p>${esc(error.message)}</p><button class="button button-outline" id="creator-detail-back">← Back to creators</button></div>`;
      $('#creator-detail-back').onclick = () => navigate('discover');
    }
  }
  async function renderYouTubeDetails(channelId) {
    const page = $('#page'); page.innerHTML = `<div class="loading">Fetching fresh public YouTube channel data…</div>`;
    try {
      const channel = await api(`/creators/youtube/${encodeURIComponent(channelId)}`);
      const subs = channel.subscriber_count_hidden ? 'Hidden by channel owner' : number(channel.followers);
      const channelUrl = `https://www.youtube.com/channel/${encodeURIComponent(channel.channel_id)}`;
      page.innerHTML = `<div class="creator-detail-top"><button class="button button-outline" id="youtube-detail-back">← Back to YouTube search</button><span class="eyebrow">PUBLIC YOUTUBE CHANNEL · ${esc(channel.channel_id)}</span></div><section class="creator-detail-hero"><div class="detail-monogram">▶</div><div><div class="eyebrow">${esc(channel.country || 'YouTube creator')}</div><h1>${esc(channel.title || channel.channel_id)}</h1><p class="subhead">${esc(channel.custom_url ? `@${channel.custom_url.replace(/^@/, '')}` : channel.channel_id)} · ${channel.published_at ? `Joined ${esc(channel.published_at.slice(0, 10))}` : 'Public channel profile'}</p><p>${esc(channel.description || 'No public channel description.')}</p></div><a class="button button-dark" href="${esc(channelUrl)}" target="_blank" rel="noopener noreferrer">Open YouTube ↗</a></section><div class="analytics-metrics youtube-detail-metrics"><div><small>Subscribers</small><strong>${subs}</strong></div><div><small>Total channel views</small><strong>${number(channel.total_views)}</strong></div><div><small>Published videos</small><strong>${number(channel.total_posts)}</strong></div></div><section class="youtube-data-note"><span>LIVE PUBLIC DATA</span><p>These are raw channel statistics returned by YouTube. Engagement rate, average views per video, audience demographics, and campaign impact are not available from this channel lookup, so Folio does not estimate them here.</p><small>Fetched now · Data source: YouTube Data API v3</small></section>`;
      $('#youtube-detail-back').onclick = () => navigate('discover');
    } catch (error) {
      page.innerHTML = `<div class="error-state"><h2>Public channel data couldn’t load</h2><p>${esc(error.message)}</p><button class="button button-outline" id="youtube-detail-back">← Back to YouTube search</button></div>`;
      $('#youtube-detail-back').onclick = () => navigate('discover');
    }
  }
  async function inviteCreator(creatorId) {
    if (!state.user) { openAuth('register', 'brand'); toast('Create a company account to invite creators'); return; } if (state.user.role !== 'brand') { toast('Creator invitations are available to company accounts'); return; }
    try { state.campaigns = await api('/campaigns/brand/' + state.profile?.brand_id); } catch { state.campaigns = []; } const active = state.campaigns.filter(c => c.status === 'active');
    if (!active.length) { openCampaignDialog(); toast('Create a campaign first, then send an invite'); return; }
    $('#campaign-content').innerHTML = `<div class="eyebrow">Creator invite</div><h2>Choose a campaign</h2><p class="dialog-intro">Invite this creator to one of your active campaigns.</p><form class="auth-form" id="invite-form"><label class="field"><span>Campaign</span><select name="campaign_id" required>${active.map(c => `<option value="${c.campaign_id}">${esc(c.campaign_name)} · ${money(c.budget)}</option>`).join('')}</select></label><label class="field"><span>Your offer (USD)</span><input name="amount" type="number" min="1" step="1" placeholder="500" required /></label><p class="form-message" id="invite-message"></p><button class="button button-dark">Send invite ↗</button></form>`; $('#campaign-dialog').showModal();
    $('#invite-form').onsubmit = async e => { e.preventDefault(); const form = new FormData(e.currentTarget), campaign = active.find(c => c.campaign_id === Number(form.get('campaign_id'))); try { await api('/sponsorships/', { method: 'POST', body: JSON.stringify({ creator_id: creatorId, campaign_id: campaign.campaign_id, agreed_amount: Number(form.get('amount')) }) }); $('#campaign-dialog').close(); toast('Invite sent successfully'); } catch (error) { $('#invite-message').textContent = error.message; } };
  }
  async function renderCampaigns() {
    const page = $('#page'); if (state.user?.role === 'creator') return renderOpenCampaigns(); if (!state.user || state.user.role !== 'brand') { page.innerHTML = authWall('Campaigns made for better collabs', 'Sign in with a company account to create campaigns, set your goals, and discover the best-fit creators.'); return; }
    if (!state.profile) { page.innerHTML = `<div class="heading-row"><div><div class="eyebrow">Your workspace</div><h1>Campaigns</h1><p class="subhead">Set up your company profile first to launch a campaign.</p></div></div>${authWall('Finish your company profile', 'Add your company details to create campaigns and start meeting creators.')}`; return; }
    page.innerHTML = `<div class="heading-row"><div><div class="eyebrow">Campaign studio</div><h1>Your campaigns</h1><p class="subhead">Manage briefs and connect with creators who fit your goals.</p></div><button class="button button-dark" id="new-campaign">Create campaign ＋</button></div><div class="stats-row" id="campaign-stats"></div><div class="section-heading"><h2>All campaigns</h2><span class="subhead">Your brand’s active and past briefs</span></div><div class="campaign-list" id="campaign-list"><div class="loading">Loading campaigns…</div></div>`; $('#new-campaign').onclick = openCampaignDialog;
    try { state.campaigns = await api(`/campaigns/brand/${state.profile.brand_id}`); } catch (error) { $('#campaign-list').innerHTML = `<div class="error-state"><h2>Campaigns could not load</h2><p>${esc(error.message)}</p></div>`; return; }
    const active = state.campaigns.filter(c => c.status === 'active').length;
    $('#campaign-stats').innerHTML = `<div class="metric-card"><span>Total campaigns</span><strong>${state.campaigns.length}</strong><small>Across your workspace</small></div><div class="metric-card"><span>Active campaigns</span><strong>${active}</strong><small>Open for creator matches</small></div><div class="metric-card"><span>Total budget</span><strong>${money(state.campaigns.reduce((sum,c) => sum + Number(c.budget), 0))}</strong><small>Allocated across campaigns</small></div><div class="metric-card"><span>Brand</span><strong style="font-size:17px">${esc(state.profile.company_name)}</strong><small>${esc(state.profile.industry || 'Industry not set')}</small></div>`;
    $('#campaign-list').innerHTML = state.campaigns.length ? state.campaigns.map(c => `<article class="campaign-row"><div class="campaign-icon">✳</div><div class="campaign-info"><strong>${esc(c.campaign_name)}</strong><p>${esc(c.advertising_field || c.target_niche || 'All niches')} · ${esc(c.target_platform || 'All platforms')}${c.target_country ? ` · ${esc(c.target_country)}` : ''}</p></div><div class="campaign-budget"><strong>${money(c.budget)}</strong><small>${number(c.min_followers || 0)}${c.max_followers ? `–${number(c.max_followers)}` : '+'} followers</small></div><span class="status ${esc(c.status)}">${esc(c.status)}</span><button class="button button-light recommendations" data-id="${c.campaign_id}">Find creators ↗</button></article>`).join('') : `<div class="empty-state"><div class="empty-illustration">▤</div><h2>Your first campaign starts here</h2><p>Publish a clear brief and let performance data find your best-fit creators.</p><button class="button button-dark" id="empty-new-campaign">Create your first campaign</button></div>`;
    $('#empty-new-campaign')?.addEventListener('click', openCampaignDialog); $$('.recommendations').forEach(button => button.onclick = () => showRecommendations(Number(button.dataset.id)));
  }
  async function renderOpenCampaigns() {
    const page = $('#page');
    if (!state.profile) { page.innerHTML = authWall('Complete your creator profile', 'Add your creator profile before applying to campaigns.'); return; }
    page.innerHTML = `<div class="heading-row"><div><div class="eyebrow">Open opportunities</div><h1>Campaigns for creators</h1><p class="subhead">Apply to brand briefs that match your audience and interests.</p></div></div><div class="campaign-list" id="open-campaigns"><div class="loading">Loading open campaigns…</div></div>`;
    try {
      const [campaigns, applications] = await Promise.all([api('/campaigns/'), api(`/sponsorships/creator/${state.profile.creator_id}`)]);
      const byCampaign = new Map(applications.map(item => [item.campaign_id, item]));
      $('#open-campaigns').innerHTML = campaigns.length ? campaigns.map(c => { const application = byCampaign.get(c.campaign_id); return `<article class="campaign-row"><div class="campaign-icon">✳</div><div class="campaign-info"><strong>${esc(c.campaign_name)}</strong><p>${esc(c.advertising_field || c.target_niche || 'Open category')} · ${esc(c.target_platform || 'Any platform')}${c.target_country ? ` · ${esc(c.target_country)}` : ''}</p><p>${esc(c.description || 'Brand is looking for creators to join this campaign.')}</p></div><div class="campaign-budget"><strong>${money(c.budget)}</strong><small>${number(c.min_followers || 0)}${c.max_followers ? `–${number(c.max_followers)}` : '+'} followers</small></div>${application ? `<span class="status ${esc(application.status)}">${esc(application.initiated_by === 'creator' ? `Application ${application.status}` : `Offer ${application.status}`)}</span>` : `<button class="button button-dark apply-campaign" data-id="${c.campaign_id}">Apply ↗</button>`}</article>`; }).join('') : `<div class="empty-state"><div class="empty-illustration">▤</div><h2>No open campaigns right now</h2><p>Check back soon for new brand briefs.</p></div>`;
      $$('.apply-campaign').forEach(button => button.onclick = () => openApplicationDialog(campaigns.find(item => item.campaign_id === Number(button.dataset.id))));
    } catch (error) { $('#open-campaigns').innerHTML = `<div class="error-state"><h2>Campaigns couldn’t load</h2><p>${esc(error.message)}</p></div>`; }
  }
  function openApplicationDialog(campaign) {
    if (!state.user || state.user.role !== 'creator') { openAuth('register'); return; }
    $('#campaign-content').innerHTML = `<div class="eyebrow">Creator application</div><h2>Apply to ${esc(campaign.campaign_name)}</h2><p class="dialog-intro">Tell the brand why your audience and content fit this brief.</p><form class="form-grid" id="application-form"><label class="field"><span>Your proposed rate (USD) *</span><input name="agreed_amount" type="number" min="1" max="${Number(campaign.budget)}" step="1" required placeholder="500" /></label><label class="field"><span>Campaign budget</span><input value="${money(campaign.budget)}" disabled /></label><label class="field full"><span>Application message</span><textarea name="application_message" maxlength="2000" placeholder="Share relevant work, audience context, and the outcome you can deliver."></textarea></label><p class="form-message full" id="application-message"></p><button class="button button-dark full">Send application ↗</button></form>`;
    $('#campaign-dialog').showModal(); $('#application-form').onsubmit = async event => { event.preventDefault(); const data = Object.fromEntries(new FormData(event.currentTarget)); data.campaign_id = campaign.campaign_id; data.agreed_amount = Number(data.agreed_amount); try { await api('/sponsorships/applications', { method: 'POST', body: JSON.stringify(data) }); $('#campaign-dialog').close(); toast('Application sent — it will stay pending until the brand responds'); await renderOpenCampaigns(); } catch (error) { $('#application-message').textContent = error.message; } };
  }
  async function reportCampaignResults(sponsorshipId) {
    const existing = await api(`/sponsorships/${sponsorshipId}/results`).catch(() => null);
    $('#campaign-content').innerHTML = `<div class="eyebrow">Campaign measurement</div><h2>Report creator results</h2><p class="dialog-intro">Enter the campaign outcome totals shared with your creator. The report can be updated as results settle.</p><form class="form-grid" id="results-form"><label class="field"><span>Impressions</span><input name="impressions" type="number" min="0" required value="${existing?.impressions ?? 0}" /></label><label class="field"><span>Clicks</span><input name="clicks" type="number" min="0" required value="${existing?.clicks ?? 0}" /></label><label class="field"><span>Conversions</span><input name="conversions" type="number" min="0" required value="${existing?.conversions ?? 0}" /></label><label class="field"><span>Attributed revenue (USD)</span><input name="attributed_revenue" type="number" min="0" step="0.01" required value="${existing?.attributed_revenue ?? 0}" /></label><label class="field"><span>Reporting date</span><input name="reported_at" type="date" required value="${esc(existing?.reported_at || new Date().toISOString().slice(0, 10))}" /></label><p class="form-message full" id="results-message"></p><button class="button button-dark full">Save campaign results</button></form>`;
    $('#campaign-dialog').showModal(); $('#results-form').onsubmit = async event => { event.preventDefault(); const data = Object.fromEntries(new FormData(event.currentTarget)); for (const key of ['impressions','clicks','conversions']) data[key] = Number(data[key]); data.attributed_revenue = Number(data.attributed_revenue); try { await api(`/sponsorships/${sponsorshipId}/results`, { method: 'PUT', body: JSON.stringify(data) }); $('#campaign-dialog').close(); toast('Campaign results saved'); } catch(error) { $('#results-message').textContent = error.message; } };
  }
  async function showRecommendations(campaignId) {
    const campaign = state.campaigns.find(item => item.campaign_id === campaignId); if (!campaign) return;
    $('#page').innerHTML = `<div class="heading-row"><div><button class="button button-outline" id="back-campaigns">← Campaigns</button><div class="eyebrow" style="margin-top:17px">Campaign matches</div><h1>${esc(campaign.campaign_name)}</h1><p class="subhead">Creators matched to your brief, ranked by fit and performance.</p></div></div><div class="creator-grid" id="recommendation-grid"><div class="loading">Scoring creator matches…</div></div>`;
    $('#back-campaigns').onclick = () => navigate('campaigns');
    try { const matches = await api(`/campaigns/${campaignId}/recommendations`); $('#recommendation-grid').innerHTML = matches.length ? matches.map(creatorCard).join('') : `<div class="empty-state"><div class="empty-illustration">⌕</div><h2>No matches yet</h2><p>Add creator metric snapshots that fit your campaign filters, then check back.</p></div>`; $$('.invite-creator').forEach(button => button.onclick = () => inviteCreator(Number(button.dataset.id))); }
    catch (error) { $('#recommendation-grid').innerHTML = `<div class="error-state"><h2>Matches couldn’t load</h2><p>${esc(error.message)}</p></div>`; }
  }
  function openCampaignDialog() {
    if (!state.user) { openAuth('register', 'brand'); toast('Create a company account to launch a campaign'); return; } if (state.user.role !== 'brand') { toast('Campaigns can be created from a company account'); return; } if (!state.profile) { navigate('profile'); toast('Complete your company profile before creating a campaign'); return; }
    $('#campaign-content').innerHTML = `<div class="eyebrow">Campaign studio</div><h2>Build your creator brief</h2><p class="dialog-intro">Clear goals help our matching engine find the right creators.</p><form class="form-grid" id="campaign-form"><label class="field full"><span>Campaign name *</span><input name="campaign_name" required maxlength="200" placeholder="Summer skin, made simple" /></label><label class="field full"><span>Campaign description</span><textarea name="description" placeholder="Tell creators what you’re building and what success looks like…"></textarea></label><label class="field"><span>Budget (USD) *</span><input name="budget" type="number" min="1" step="1" required placeholder="5000" /></label><label class="field"><span>Advertising field</span><select name="advertising_field"><option value="">Choose a field</option><option>Beauty & personal care</option><option>Food & beverage</option><option>Fashion & accessories</option><option>Travel & hospitality</option><option>Fitness & wellness</option><option>Technology & gaming</option><option>Home & lifestyle</option><option>Education & finance</option><option>Parenting & family</option><option>Pets & animals</option><option>Sustainability & outdoors</option></select></label><label class="field"><span>Target niche</span><input name="target_niche" placeholder="Beauty, food, travel…" /></label><label class="field"><span>Platform</span><select name="target_platform"><option value="">Any platform</option><option>Instagram</option><option>TikTok</option><option>YouTube</option><option>Twitch</option><option>Blog</option></select></label><label class="field"><span>Target country</span><input name="target_country" placeholder="United States" /></label><label class="field"><span>Minimum followers</span><input name="min_followers" type="number" min="0" placeholder="1000" /></label><label class="field"><span>Maximum followers</span><input name="max_followers" type="number" min="0" placeholder="100000" /></label><p class="form-message full" id="campaign-message"></p><button class="button button-dark full">Publish campaign ↗</button></form>`; $('#campaign-dialog').showModal();
    $('#campaign-form').onsubmit = async event => { event.preventDefault(); const form = new FormData(event.currentTarget), body = Object.fromEntries(form.entries()); body.brand_id = state.profile.brand_id; body.budget = Number(body.budget); body.min_followers = body.min_followers ? Number(body.min_followers) : null; body.max_followers = body.max_followers ? Number(body.max_followers) : null; for (const field of ['target_niche', 'advertising_field', 'target_country', 'target_platform', 'description']) body[field] ||= null; try { await api('/campaigns/', { method: 'POST', body: JSON.stringify(body) }); $('#campaign-dialog').close(); toast('Campaign published'); await navigate('campaigns'); } catch (error) { $('#campaign-message').textContent = error.message; } };
  }
  async function renderPartnerships() {
    const page = $('#page'); if (!state.user) { page.innerHTML = authWall('Keep every partnership moving', 'Log in to follow your active collaborations, offers, and campaign progress.'); return; } if (!state.profile) { page.innerHTML = `<div class="heading-row"><div><div class="eyebrow">Collaboration desk</div><h1>Partnerships</h1><p class="subhead">Complete your profile to start making connections.</p></div></div>${authWall('Finish your profile', 'A complete profile makes it easy for the right people to find you.')}`; return; }
    const isBrand = state.user.role === 'brand', endpoint = isBrand ? `/campaigns/brand/${state.profile.brand_id}` : `/sponsorships/creator/${state.profile.creator_id}`;
    page.innerHTML = `<div class="heading-row"><div><div class="eyebrow">Collaboration desk</div><h1>Your partnerships</h1><p class="subhead">Offers and collaborations, all in one place.</p></div>${isBrand ? '<button class="button button-dark" id="partnership-new">Create campaign ＋</button>' : ''}</div><div class="partnership-list" id="partnership-list"><div class="loading">Loading partnerships…</div></div>`; $('#partnership-new')?.addEventListener('click', openCampaignDialog);
    try { let rows = await api(endpoint); if (isBrand) { const all = await Promise.all(rows.map(async campaign => ({ campaign, applications: await api(`/sponsorships/campaign/${campaign.campaign_id}`).catch(() => []) }))); rows = all.flatMap(({campaign, applications}) => applications.map(item => ({...item, campaign_name: campaign.campaign_name}))); }
      $('#partnership-list').innerHTML = rows.length ? rows.map(item => `<article class="partnership-row"><div class="campaign-icon">↗</div><div class="partnership-info"><strong>${esc(item.campaign_name || `Campaign #${item.campaign_id}`)}</strong><p>${isBrand ? `Creator #${item.creator_id}` : `Campaign #${item.campaign_id}`} · ${money(item.agreed_amount)} · ${esc(item.initiated_by === 'creator' ? 'Creator application' : 'Brand offer')}</p>${item.application_message ? `<p>${esc(item.application_message)}</p>` : ''}</div><span class="status ${esc(item.status)}">${esc(item.status)}</span>${item.status === 'pending' && isBrand && item.initiated_by === 'creator' ? `<button class="button button-light update-status" data-id="${item.sponsorship_id}" data-status="accepted">Accept</button><button class="button button-outline update-status" data-id="${item.sponsorship_id}" data-status="rejected">Decline</button>` : ''}${item.status === 'pending' && isBrand && item.initiated_by === 'brand' ? `<button class="button button-outline update-status" data-id="${item.sponsorship_id}" data-status="cancelled">Withdraw offer</button>` : ''}${item.status === 'pending' && !isBrand && item.initiated_by === 'brand' ? `<button class="button button-light update-status" data-id="${item.sponsorship_id}" data-status="accepted">Accept</button><button class="button button-outline update-status" data-id="${item.sponsorship_id}" data-status="rejected">Decline</button>` : ''}${item.status === 'pending' && !isBrand && item.initiated_by === 'creator' ? `<button class="button button-outline update-status" data-id="${item.sponsorship_id}" data-status="cancelled">Withdraw application</button>` : ''}${item.status === 'accepted' && isBrand ? `<button class="button button-light update-status" data-id="${item.sponsorship_id}" data-status="in_progress">Start collab</button>` : ''}${item.status === 'in_progress' && !isBrand ? `<button class="button button-light update-status" data-id="${item.sponsorship_id}" data-status="completed">Mark complete</button>` : ''}${isBrand && ['accepted','in_progress','completed'].includes(item.status) ? `<button class="button button-outline report-results" data-id="${item.sponsorship_id}">Report results</button>` : ''}</article>`).join('') : `<div class="empty-state"><div class="empty-illustration">↗</div><h2>No partnerships yet</h2><p>${isBrand ? 'Publish a campaign and invite creators who match your goals.' : 'Apply to an open campaign or wait for a brand offer.'}</p><button class="button button-light" data-go="${isBrand ? 'campaigns' : 'campaigns'}">${isBrand ? 'View campaigns' : 'Browse campaigns'}</button></div>`;
      $$('[data-go]').forEach(button => button.onclick = () => navigate(button.dataset.go)); $$('.update-status').forEach(button => button.onclick = async () => { try { await api(`/sponsorships/${button.dataset.id}/status`, { method: 'PATCH', body: JSON.stringify({ status: button.dataset.status }) }); toast('Partnership updated'); await renderPartnerships(); } catch(error) { toast(error.message); } });
      $$('.report-results').forEach(button => button.onclick = () => reportCampaignResults(Number(button.dataset.id)));
    } catch (error) { $('#partnership-list').innerHTML = `<div class="error-state"><h2>Partnerships couldn’t load</h2><p>${esc(error.message)}</p></div>`; }
  }
  async function renderProfile() {
    const page = $('#page'); if (!state.user) { page.innerHTML = authWall('Make your profile count', 'Create an account to tell brands what you do, what you create, and who you reach.'); return; }
    const creator = state.user.role === 'creator', profile = state.profile;
    page.innerHTML = `<div class="heading-row"><div><div class="eyebrow">Your workspace</div><h1>${creator ? 'Creator profile' : 'Brand profile'}</h1><p class="subhead">A thoughtful profile helps the right people find you.</p></div><button class="button button-outline" id="sign-out">Sign out</button></div>${!profile ? `<div class="profile-panel"><div class="profile-head"><span class="avatar">${initials(state.user.email)}</span><div><h2>Set up your ${creator ? 'creator' : 'brand'} profile</h2><p>Signed in as ${esc(state.user.email)}</p></div></div><form class="profile-form" id="profile-form">${creator ? `<label class="field"><span>Username *</span><input name="username" required maxlength="100" placeholder="yourname" /></label><label class="field"><span>Display name</span><input name="display_name" placeholder="Your name" /></label><label class="field full"><span>Bio</span><textarea name="bio" placeholder="What do you create? Who do you reach?"></textarea></label><label class="field"><span>Niche</span><input name="niche" placeholder="Food, beauty, travel…" /></label><label class="field"><span>Country</span><input name="country" placeholder="India" /></label><label class="field"><span>City</span><input name="city" placeholder="Mumbai" /></label><label class="field"><span>Social platform</span><select name="platform"><option>Instagram</option><option>TikTok</option><option>YouTube</option><option>Twitch</option><option>Blog</option></select></label><label class="field"><span>Social username</span><input name="social_username" placeholder="yourhandle" /></label><label class="field"><span>Followers</span><input name="followers" type="number" min="0" value="0" /></label>` : `<label class="field"><span>Company name *</span><input name="company_name" required maxlength="150" placeholder="Studio North" /></label><label class="field"><span>Company email *</span><input name="email" type="email" required value="${esc(state.user.email)}" /></label><label class="field"><span>Industry</span><input name="industry" placeholder="Beauty, lifestyle, tech…" /></label><label class="field"><span>Website</span><input name="website" type="url" placeholder="https://example.com" /></label>`}<p class="form-message full" id="profile-message"></p><div class="profile-actions full"><button class="button button-dark">Save profile</button></div></form></div>` : `<div class="profile-panel"><div class="profile-head"><span class="avatar">${initials(profile.display_name || profile.company_name || profile.username)}</span><div><h2>${esc(profile.display_name || profile.company_name || profile.username)}</h2><p>${creator ? `@${esc(profile.username)} · ${esc([profile.city, profile.country].filter(Boolean).join(', '))}` : esc(profile.industry || 'Brand')} · ${esc(state.user.email)}</p></div></div><form class="profile-form" id="profile-form">${creator ? `<label class="field"><span>Username</span><input name="username" value="${esc(profile.username)}" disabled /></label><label class="field"><span>Display name</span><input name="display_name" value="${esc(profile.display_name || '')}" /></label><label class="field full"><span>Bio</span><textarea name="bio">${esc(profile.bio || '')}</textarea></label><label class="field"><span>Niche</span><input name="niche" value="${esc(profile.niche || '')}" /></label><label class="field"><span>Country</span><input name="country" value="${esc(profile.country || '')}" /></label><label class="field"><span>City</span><input name="city" value="${esc(profile.city || '')}" /></label>` : `<label class="field"><span>Company name</span><input name="company_name" required value="${esc(profile.company_name || '')}" /></label><label class="field"><span>Company email</span><input name="email" type="email" required value="${esc(profile.email || state.user.email)}" /></label><label class="field"><span>Industry</span><input name="industry" value="${esc(profile.industry || '')}" /></label><label class="field"><span>Website</span><input name="website" type="url" value="${esc(profile.website || '')}" /></label>`}<p class="form-message full" id="profile-message"></p><div class="profile-actions full"><button class="button button-dark">Save changes</button></div></form>${creator ? `<div class="section-heading"><h2>Social accounts</h2><button class="button button-outline" id="add-social">Add account ＋</button></div><div class="partnership-list" id="social-list"></div>` : ''}</div>`}`;
    $('#sign-out')?.addEventListener('click', () => logout()); $('#profile-form').onsubmit = async event => { event.preventDefault(); const form = new FormData(event.currentTarget), body = Object.fromEntries(form.entries()); delete body.platform; delete body.social_username; delete body.followers; if (creator) body.email = state.user.email; const message = $('#profile-message'); try { state.profile = await api(creator ? '/creators/me' : '/brands/me', { method: profile ? 'PUT' : 'POST', body: JSON.stringify(body) }); updateAccount(); toast('Profile saved'); if (creator && !profile && form.get('social_username')) await createSocial(form); await renderProfile(); } catch (error) { message.textContent = error.message; } };
    if (profile && !state.user.google_linked) {
      page.insertAdjacentHTML('beforeend', `<section class="google-link-card"><div><div class="eyebrow">SIGN-IN SECURITY</div><strong>Connect Google to your account</strong><p>Use Google to sign in faster next time. The Google email must match ${esc(state.user.email)}.</p></div><div id="google-link"></div></section>`);
      setupGoogleButton('google-link');
    }
    if (creator && profile) {
      page.insertAdjacentHTML('beforeend', `<section class="section-block"><div class="section-heading"><div><h2>Advertising field insights</h2><p class="subhead">ML-based profile fit plus reported results from your campaigns.</p></div></div><div id="advertising-insights" class="campaign-list"><div class="loading">Analyzing your profile…</div></div><p class="subhead">Fit is inferred from profile text. Views are a reach proxy. Reported campaign outcomes are not a prediction of future sales.</p></section>`);
      await Promise.all([refreshSocial(), loadAdvertisingInsights()]);
      $('#add-social').onclick = () => { const list = $('#social-list'); list.insertAdjacentHTML('beforeend', socialForm()); bindSocialForm($('#social-create-form')); };
    }
  }
  async function loadAdvertisingInsights() {
    const container = $('#advertising-insights'); if (!container) return;
    try {
      const report = await api('/creators/me/advertising-insights');
      container.innerHTML = report.fields.map(field => `<article class="campaign-row"><div class="campaign-icon">✳</div><div class="campaign-info"><strong>${esc(field.field)} · ${Number(field.fit_score).toFixed(0)}% profile fit</strong><p>${esc(field.evidence)}</p><p>${field.reported_campaigns ? `${number(field.impressions)} impressions · ${number(field.clicks)} clicks · ${number(field.conversions)} conversions · ${money(field.attributed_revenue)} reported revenue` : field.estimated_views_per_post ? `Typical audience exposure: ${number(field.estimated_views_per_post)} views per post` : 'Add social performance metrics and ask brands to report campaign results.'}</p></div>${field.click_through_rate != null ? `<span class="status">${field.click_through_rate}% CTR</span>` : ''}</article>`).join('') || `<div class="empty-state"><h2>Add profile details for insights</h2><p>Describe your niche and the content you make.</p></div>`;
    } catch (error) { container.innerHTML = `<div class="error-state"><h2>Insights are not ready yet</h2><p>${esc(error.message)}</p></div>`; }
  }
  function socialForm() { return `<form id="social-create-form" class="campaign-row" style="flex-wrap:wrap"><label class="field"><span>Platform</span><select name="platform"><option>Instagram</option><option>TikTok</option><option>YouTube</option><option>Twitch</option><option>Blog</option></select></label><label class="field"><span>Username</span><input name="username" required /></label><label class="field"><span>Profile URL</span><input name="profile_url" type="url" placeholder="https://…" /></label><label class="field"><span>Followers</span><input name="followers" type="number" min="0" value="0" /></label><button class="button button-dark">Add account</button></form>`; }
  function bindSocialForm(form) { form.onsubmit = async event => { event.preventDefault(); const data = Object.fromEntries(new FormData(form)); data.creator_id = state.profile.creator_id; data.followers = Number(data.followers || 0); if (!data.profile_url) delete data.profile_url; try { await api('/social-accounts/', { method: 'POST', body: JSON.stringify(data) }); toast('Social account added'); await refreshSocial(); } catch (error) { toast(error.message); } }; }
  async function createSocial(form) { const data = Object.fromEntries(form.entries()); if (!data.social_username) return; try { const account = await api('/social-accounts/', { method: 'POST', body: JSON.stringify({ creator_id: state.profile.creator_id, platform: data.platform, username: data.social_username, followers: Number(data.followers || 0) }) }); if (Number(data.followers) > 0) await api('/creator-metrics/', { method: 'POST', body: JSON.stringify({ account_id: account.account_id, followers: Number(data.followers), metric_date: new Date().toISOString().slice(0, 10) }) }); } catch(error) { toast(error.message); } }
  async function refreshSocial() {
    const list = $('#social-list'); if (!list || !state.profile) return;
    try {
      const accounts = await api(`/social-accounts/creator/${state.profile.creator_id}`);
      const rows = await Promise.all(accounts.map(async account => {
        let metric = null;
        if (['youtube', 'you tube'].includes(account.platform.toLowerCase())) metric = await api(`/creator-metrics/account/${account.account_id}/latest`).catch(() => null);
        return `<article class="partnership-row"><div class="campaign-icon">◎</div><div class="partnership-info"><strong>${esc(account.platform)} · @${esc(account.username)}</strong><p>${metric?.data_source === 'youtube_public' ? `${number(metric.followers)} subscribers · ${number(metric.total_views)} lifetime views · synced ${esc(metric.metric_date)}` : `${number(account.followers)} followers`}${account.profile_url ? ` · <a href="${esc(account.profile_url)}" target="_blank" rel="noreferrer">View profile ↗</a>` : ''}</p></div>${['youtube','you tube'].includes(account.platform.toLowerCase()) ? `<button class="button button-light sync-youtube" data-id="${account.account_id}">Sync YouTube data</button>` : ''}</article>`;
      }));
      list.innerHTML = `${rows.join('')}${socialForm()}`; bindSocialForm($('#social-create-form'));
      $$('.sync-youtube', list).forEach(button => button.onclick = async () => { button.disabled = true; button.textContent = 'Syncing…'; try { const result = await api(`/social-accounts/${button.dataset.id}/sync-youtube`, { method: 'POST' }); toast(`Synced ${number(result.followers)} subscribers`); await refreshSocial(); } catch (error) { toast(error.message); button.disabled = false; button.textContent = 'Sync YouTube data'; } });
    } catch(error) { list.innerHTML = `<p class="subhead">${esc(error.message)}</p>`; }
  }
  function openAuth(mode = 'login', role = state.authRole) { state.authMode = mode; state.authRole = role; renderAuth(); $('#auth-dialog').showModal(); }
  async function finishAuth(auth, mode) {
    localStorage.setItem('creator_marketplace_token', auth.access_token);
    state.user = { user_id: auth.user_id, email: auth.email, role: auth.role, creator_id: auth.creator_id || null, brand_id: auth.brand_id || null, google_linked: Boolean(auth.google_linked) };
    state.profile = null; await loadProfile(); $('#auth-dialog').close(); updateAccount();
    toast(mode === 'login' ? 'Welcome back' : 'Your account is ready'); await navigate('profile');
  }
  function setupGoogleButton(targetId = 'google-signin') {
    const container = $(`#${targetId}`); if (!container) return;
    const showGoogleSetup = detail => {
      container.innerHTML = `<button class="google-glass-button" type="button"><span class="google-mark">G</span><span>Continue with Google</span><span class="google-arrow">↗</span></button><p class="google-config-hint">${esc(detail)}</p>`;
      $('.google-glass-button', container).onclick = () => toast('Google sign-in needs a Google client ID. See the setup note below the button.');
    };
    if (!state.googleClientId) { showGoogleSetup('Google sign-in needs GOOGLE_CLIENT_ID configured by the site owner.'); return; }
    if (!window.google?.accounts?.id) {
      const attempts = Number(container.dataset.oauthTries || 0);
      if (attempts >= 24) { showGoogleSetup('Google sign-in could not load. Check your connection and refresh.'); return; }
      container.dataset.oauthTries = String(attempts + 1); setTimeout(() => setupGoogleButton(targetId), 180); return;
    }
    window.google.accounts.id.initialize({
      client_id: state.googleClientId,
      callback: async response => {
        const message = $('#auth-message');
        try {
          if (targetId === 'google-link') {
            await api('/auth/google/link', { method: 'POST', body: JSON.stringify({ credential: response.credential }) });
            state.user.google_linked = true; toast('Google account connected'); await navigate('profile'); return;
          }
          const routeRole = state.authRole === 'creator' ? 'creator' : 'company';
          const auth = await api(`/auth/${routeRole}/google`, { method: 'POST', body: JSON.stringify({ credential: response.credential }) });
          await finishAuth(auth, state.authMode);
        } catch (error) { if (message) message.textContent = error.message; }
      },
      auto_select: false,
    });
    window.google.accounts.id.renderButton(container, {
      theme: 'outline', size: 'large', shape: 'pill', text: state.authMode === 'login' ? 'signin_with' : 'signup_with',
      width: Math.min(360, Math.max(250, Math.floor(container.clientWidth || 320))), logo_alignment: 'left',
    });
  }
  function renderAuth() {
    const mode = state.authMode, role = state.authRole, creator = role === 'creator';
    const roleLabel = creator ? 'creator' : 'company';
    $('#auth-content').innerHTML = `<div class="auth-eyebrow"><span class="auth-brand-dot">f</span> FOLIO ACCOUNT</div><h2>${mode === 'login' ? 'Welcome back.' : 'Make your next move.'}</h2><p class="dialog-intro">${mode === 'login' ? 'Sign in to your workspace and pick up where you left off.' : 'One account. Better partnerships. Built around you.'}</p><div class="auth-role-switch" aria-label="Choose account type"><button data-auth-role-switch="creator" class="${creator ? 'active' : ''}"><span class="role-glyph">✳</span><span>Creator<small>Grow your influence</small></span></button><button data-auth-role-switch="brand" class="${!creator ? 'active' : ''}"><span class="role-glyph">◈</span><span>Company<small>Build a campaign</small></span></button></div><div class="auth-switch"><button data-mode="login" class="${mode === 'login' ? 'active' : ''}">Sign in</button><button data-mode="register" class="${mode === 'register' ? 'active' : ''}">Create account</button></div><div class="google-signin-wrap"><div id="google-signin"></div></div><div class="auth-divider"><span>or continue with email</span></div><form class="auth-form" id="auth-form"><label class="field"><span>Work email</span><input name="email" type="email" required autocomplete="email" placeholder="you@example.com" /></label><label class="field"><span>Password</span><input name="password" type="password" required minlength="8" autocomplete="${mode === 'login' ? 'current-password' : 'new-password'}" placeholder="At least 8 characters" /></label><p class="form-message" id="auth-message"></p><button class="button button-dark auth-submit">${mode === 'login' ? 'Sign in as a ' + roleLabel : 'Create ' + (creator ? 'creator' : 'company') + ' account'} <span>↗</span></button></form><p class="auth-note">Protected sign-in · Your profile stays in your control</p>`;
    $$('[data-mode]').forEach(button => button.onclick = () => { state.authMode = button.dataset.mode; renderAuth(); });
    $$('[data-auth-role-switch]').forEach(button => button.onclick = () => { state.authRole = button.dataset.authRoleSwitch; renderAuth(); });
    $('#auth-form').onsubmit = async event => {
      event.preventDefault(); const data = Object.fromEntries(new FormData(event.currentTarget));
      const routeRole = creator ? 'creator' : 'company';
      try {
        const auth = await api(`/auth/${routeRole}/${mode === 'login' ? 'login' : 'register'}`, { method: 'POST', body: JSON.stringify(data) });
        await finishAuth(auth, mode);
      } catch (error) { $('#auth-message').textContent = error.message; }
    };
    setupGoogleButton();
  }
  function logout(showToast = true) { localStorage.removeItem('creator_marketplace_token'); state.user = null; state.profile = null; updateAccount(); if (showToast) toast('You’ve signed out'); navigate('discover'); }
  $$('.nav-item').forEach(button => button.addEventListener('click', () => navigate(button.dataset.view)));
  setTheme(localStorage.getItem('creator_marketplace_theme') || 'light');
  $('#theme-toggle').addEventListener('click', () => setTheme(document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark'));
  $('#top-cta').addEventListener('click', () => state.user?.role === 'brand' ? openCampaignDialog() : state.user ? toast('You’re signed in as a creator. Switch to a company account to create campaigns.') : openAuth('register', 'brand'));
  $('#header-sign-in').addEventListener('click', async () => {
    if (localStorage.getItem('creator_marketplace_token') && !state.user) {
      try { state.user = await api('/auth/me'); await loadProfile(); updateAccount(); await navigate('profile'); }
      catch (error) { if (error.status === 401) logout(false); else { toast('The saved session could not be checked. Make sure the API is running.'); return; } }
      if (!state.user) openAuth('login', 'brand');
      return;
    }
    openAuth('login', 'brand');
  });
  $('#account-button').addEventListener('click', () => state.user ? navigate('profile') : openAuth('login', 'brand'));
  $('#assistant-launch').addEventListener('click', () => {
    if (!state.user) { openAuth('login', 'brand'); toast('Sign in to ask about your marketplace data'); return; }
    $('#assistant-dialog').showModal(); $('#assistant-question').focus();
  });
  $('#assistant-clear').addEventListener('click', () => {
    state.assistantConversation = [];
    $('#assistant-messages').innerHTML = `<div class="assistant-welcome"><strong>Your marketplace copilot</strong><p>Ask for a creator shortlist, unpack campaign results, or understand your advertising impact. I’ll cite the records I use and say when data is missing.</p><div class="assistant-starters"><button type="button">Find creators for my next campaign</button><button type="button">Where am I getting the most impact?</button><button type="button">Summarize my latest results</button></div></div>`;
  });
  $('#assistant-messages').addEventListener('click', event => {
    const starter = event.target.closest('.assistant-starters button, .assistant-suggestions button');
    if (!starter) return;
    $('#assistant-question').value = starter.textContent.trim(); $('#assistant-form').requestSubmit();
  });
  $('#assistant-question').addEventListener('input', event => { event.target.style.height = 'auto'; event.target.style.height = `${Math.min(event.target.scrollHeight, 120)}px`; });
  $('#assistant-form').addEventListener('submit', async event => {
    event.preventDefault();
    const input = $('#assistant-question'), question = input.value.trim(), messages = $('#assistant-messages');
    if (question.length < 3) return;
    messages.insertAdjacentHTML('beforeend', `<div class="assistant-message assistant-user">${esc(question)}</div><div class="assistant-message assistant-pending">Checking marketplace records…</div>`);
    messages.scrollTop = messages.scrollHeight; input.value = ''; input.disabled = true; $('button[type="submit"]', event.currentTarget).disabled = true;
    try {
      const result = await api('/intelligence/ask', { method: 'POST', body: JSON.stringify({ question, conversation: state.assistantConversation.slice(-8) }) });
      $('.assistant-pending', messages)?.remove();
      const sourceCards = result.sources.map(source => {
        const facts = Object.entries(source.facts).filter(([, value]) => value !== null && value !== '' && !String(value).includes('company-only')).slice(0, 5).map(([key, value]) => `<span>${esc(key.replaceAll('_', ' '))}: ${esc(Array.isArray(value) ? value.join(', ') : typeof value === 'object' ? JSON.stringify(value) : value)}</span>`).join('');
        return `<article class="assistant-source"><strong>${esc(source.label)}</strong><small>${esc(source.kind.replaceAll('_', ' '))}</small><div>${facts}</div></article>`;
      }).join('');
      const suggestions = (result.suggested_questions || []).slice(0, 3).map(item => `<button type="button">${esc(item)}</button>`).join('');
      messages.insertAdjacentHTML('beforeend', `<div class="assistant-answer"><div class="assistant-provider">${result.provider === 'openai' ? 'OPENAI · SOURCED' : 'LOCAL DATA · SOURCED'}</div><p>${esc(result.answer).replaceAll('\n', '<br>')}</p>${sourceCards ? `<div class="assistant-sources"><strong>Records used</strong>${sourceCards}</div>` : '<small>No supporting records found in your workspace.</small>'}${suggestions ? `<div class="assistant-suggestions"><span>Continue exploring</span>${suggestions}</div>` : ''}</div>`);
      state.assistantConversation.push({ role: 'user', content: question }, { role: 'assistant', content: result.answer });
      state.assistantConversation = state.assistantConversation.slice(-8);
    } catch (error) {
      $('.assistant-pending', messages)?.remove();
      messages.insertAdjacentHTML('beforeend', `<div class="assistant-answer"><p>${esc(error.message)}</p></div>`);
    } finally { input.disabled = false; $('button[type="submit"]', event.currentTarget).disabled = false; input.focus(); messages.scrollTop = messages.scrollHeight; }
  });
  document.addEventListener('click', event => { const auth = event.target.closest('[data-auth]'); if (auth) openAuth(auth.dataset.auth, auth.dataset.authRole || state.authRole); const go = event.target.closest('[data-go]'); if (go) navigate(go.dataset.go); });
  window.addEventListener('hashchange', () => { const view = location.hash.slice(1); if (view && view !== state.view) navigate(view); });
  initialize();
})();
