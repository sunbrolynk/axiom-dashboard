/**
 * App entry point — state management, data loading, event binding.
 *
 * Orchestrates map.js and ui.js:
 *   1. User selects time range or clicks refresh
 *   2. loadData() fetches from /api/geodata and /api/stats
 *   3. Passes results to renderMap() and renderUI()
 */

let selectedHours = 168;

// ── Service Worker Registration ────────────────────────────
if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/service-worker.js')
        .then(reg => console.log('SW registered:', reg.scope))
        .catch(err => console.log('SW registration failed:', err));
}

// ── Time Range Pills ───────────────────────────────────────
document.querySelectorAll('.pill-option').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.pill-option').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        selectedHours = parseInt(btn.dataset.hours);
        loadData();
    });
});

// ── Data Loading ───────────────────────────────────────────
async function loadData() {
    const btn = document.getElementById('refresh-btn');
    const loading = document.getElementById('loading');

    btn.disabled = true;
    btn.classList.add('loading');
    loading.classList.remove('hidden');

    try {
        const [geoRes, statsRes] = await Promise.all([
            fetch(`/api/geodata?hours=${selectedHours}`),
            fetch(`/api/stats?hours=${selectedHours}`),
        ]);

        const geodata = await geoRes.json();
        const statsData = await statsRes.json();

        renderMap(geodata);
        renderUI(geodata, statsData);

        document.getElementById('last-updated').textContent =
            new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch (err) {
        console.error('Load failed:', err);
    } finally {
        btn.disabled = false;
        btn.classList.remove('loading');
        loading.classList.add('hidden');
    }
}
