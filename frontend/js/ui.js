/**
 * UI Rendering — populates stats, IP list, status codes, endpoints.
 *
 * Renders to both desktop (side panel) and mobile (bottom sheet)
 * containers simultaneously since they show the same data.
 */

function renderUI(geodata, statsData) {
    // ── Stat cards ─────────────────────────────────────────
    const totalReqs = geodata.reduce((sum, d) => sum + d.request_count, 0);
    const uniqueCities = new Set(geodata.map(d => d.city)).size;

    document.getElementById('total-requests').textContent = totalReqs.toLocaleString();
    document.getElementById('unique-ips').textContent = geodata.length.toLocaleString();
    document.getElementById('total-locations').textContent = uniqueCities;

    const statuses = statsData.status_codes || [];
    const totalFromStatus = statuses.reduce((s, d) => s + d.count, 0);
    const errors = statuses.filter(d => d.status >= 400).reduce((s, d) => s + d.count, 0);
    const errPct = totalFromStatus > 0 ? ((errors / totalFromStatus) * 100).toFixed(1) : 0;

    const errEl = document.getElementById('error-rate');
    errEl.textContent = errPct + '%';
    errEl.className = 'value ' + (errPct > 10 ? 'red' : errPct > 5 ? 'yellow' : 'green');

    // ── IP list ────────────────────────────────────────────
    const maxReqs = geodata.length ? geodata[0].request_count : 1;

    const ipHtml = geodata.slice(0, 15).map((d, i) => {
        const pct = (d.request_count / maxReqs) * 100;
        return `
            <div class="ip-row" onclick="panTo(${d.lat}, ${d.lng})">
                <div class="ip-rank">${i + 1}</div>
                <div class="ip-bar" style="opacity: ${0.3 + (pct / 100) * 0.7}"></div>
                <div class="ip-info">
                    <div class="ip-addr">${d.ip}</div>
                    <div class="ip-location">${d.city}, ${d.country_code}</div>
                </div>
                <div class="ip-count">${formatCount(d.request_count)}</div>
            </div>`;
    }).join('');

    // ── Status codes ───────────────────────────────────────
    const statusHtml = statuses.map(d => {
        const cls = d.status < 300 ? 's2xx' : d.status < 500 ? 's4xx' : 's5xx';
        return `
            <div class="status-pill">
                <div class="status-dot ${cls}"></div>
                <span class="status-code">${d.status}</span>
                <span class="status-count">${formatCount(d.count)}</span>
            </div>`;
    }).join('');

    // ── Endpoints ──────────────────────────────────────────
    const endpoints = (statsData.top_endpoints || []).filter(d => d.url);

    const epHtml = endpoints.slice(0, 15).map(d => `
        <div class="ep-row">
            <span class="ep-path" title="${d.url}">${d.url}</span>
            <span class="ep-hits">${formatCount(d.hits)}</span>
        </div>
    `).join('');

    // ── Apply to both desktop and mobile containers ────────
    const targets = [
        { ip: 'ip-list', ipCount: 'ip-count', status: 'status-list', ep: 'ep-list', epCount: 'ep-count' },
        { ip: 'm-ip-list', ipCount: 'm-ip-count', status: 'm-status-list', ep: 'm-ep-list', epCount: 'm-ep-count' },
    ];

    targets.forEach(t => {
        document.getElementById(t.ipCount).textContent = `${geodata.length} IPs`;
        document.getElementById(t.ip).innerHTML = ipHtml;
        document.getElementById(t.status).innerHTML = statusHtml;
        document.getElementById(t.epCount).textContent = endpoints.length;
        document.getElementById(t.ep).innerHTML = epHtml;
    });
}


function formatCount(n) {
    if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
    if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
    return n.toLocaleString();
}


function toggleSheet() {
    document.getElementById('bottom-sheet').classList.toggle('open');
    document.getElementById('sheet-backdrop').classList.toggle('open');
}
