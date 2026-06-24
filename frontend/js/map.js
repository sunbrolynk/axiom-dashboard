/**
 * Google Maps — deck.gl heatmap + AdvancedMarkerElement.
 *
 * Migration (June 2026):
 *   - google.maps.visualization.HeatmapLayer → deck.gl HeatmapLayer
 *   - google.maps.Marker → google.maps.marker.AdvancedMarkerElement
 *   - libraries=visualization → libraries=marker
 *   - Map requires mapId for AdvancedMarkerElement
 *
 * Zoom-level strategy:
 *   < 8  → deck.gl HeatmapLayer (density blobs)
 *   >= 8 → Individual AdvancedMarkerElement with click info windows
 */

/* global google, deck */

let map, infoWindow, deckOverlay;
let markers = [];
let currentGeodata = [];

// Dark map styling (applied via Cloud Console for vector maps,
// but we keep this as fallback for raster)
const MAP_STYLES = [
    { elementType: 'geometry', stylers: [{ color: '#0d1117' }] },
    { elementType: 'labels.text.stroke', stylers: [{ color: '#0d1117' }] },
    { elementType: 'labels.text.fill', stylers: [{ color: '#3b4252' }] },
    { featureType: 'administrative', elementType: 'geometry.stroke', stylers: [{ color: '#1e2939' }] },
    { featureType: 'administrative.country', elementType: 'geometry.stroke', stylers: [{ color: '#2e3a50' }] },
    { featureType: 'road', elementType: 'geometry', stylers: [{ color: '#161b22' }] },
    { featureType: 'road', elementType: 'geometry.stroke', stylers: [{ color: '#1e2939' }] },
    { featureType: 'water', elementType: 'geometry', stylers: [{ color: '#090e16' }] },
    { featureType: 'poi', stylers: [{ visibility: 'off' }] },
    { featureType: 'transit', stylers: [{ visibility: 'off' }] },
];


function initMap() {
    map = new google.maps.Map(document.getElementById('map'), {
        zoom: 4,
        center: { lat: 39.8283, lng: -98.5795 },
        mapTypeId: 'roadmap',
        disableDefaultUI: true,
        zoomControl: true,
        gestureHandling: 'greedy',
        zoomControlOptions: { position: google.maps.ControlPosition.LEFT_CENTER },
        styles: MAP_STYLES,
        mapId: 'DEMO_MAP_ID',
    });

    infoWindow = new google.maps.InfoWindow();

    // Initialize deck.gl overlay (starts with no layers)
    deckOverlay = new deck.GoogleMapsOverlay({ layers: [] });
    deckOverlay.setMap(map);

    // Switch between heatmap and markers based on zoom level
    map.addListener('zoom_changed', () => {
        updateVisibility();
    });

    // Trigger initial data load (defined in app.js)
    loadData();
}


function updateVisibility() {
    const zoom = map.getZoom();
    const showHeatmap = zoom < 8;

    // Toggle deck.gl heatmap
    if (deckOverlay && currentGeodata.length) {
        deckOverlay.setProps({
            layers: showHeatmap ? [createHeatmapLayer(currentGeodata)] : [],
        });
    }

    // Toggle markers
    markers.forEach(m => {
        m.marker.map = showHeatmap ? null : map;
    });
}


function createHeatmapLayer(geodata) {
    return new deck.HeatmapLayer({
        id: 'heatmap',
        data: geodata,
        getPosition: d => [d.lng, d.lat],
        getWeight: d => d.request_count,
        radiusPixels: 50,
        intensity: 1,
        threshold: 0.05,
        colorRange: [
            [99, 102, 241, 50],    // indigo, low opacity
            [99, 102, 241, 100],   // indigo
            [139, 92, 246, 150],   // purple
            [168, 85, 247, 180],   // violet
            [236, 72, 153, 200],   // pink
            [239, 68, 68, 230],    // red
            [255, 255, 255, 255],  // white (hottest)
        ],
    });
}


function createMarkerElement(requestCount) {
    /**
     * Build a custom HTML element for AdvancedMarkerElement.
     * Replaces the old google.maps.Marker circle icon.
     */
    const size = Math.max(16, Math.log2(requestCount + 1) * 7);
    const el = document.createElement('div');
    el.style.width = size + 'px';
    el.style.height = size + 'px';
    el.style.borderRadius = '50%';
    el.style.backgroundColor = 'rgba(99, 102, 241, 0.85)';
    el.style.border = '2px solid #a5b4fc';
    el.style.cursor = 'pointer';
    el.style.transition = 'transform 0.15s';
    el.addEventListener('mouseenter', () => { el.style.transform = 'scale(1.2)'; });
    el.addEventListener('mouseleave', () => { el.style.transform = 'scale(1)'; });
    return el;
}


function renderMap(geodata) {
    // Clear existing markers
    markers.forEach(m => { m.marker.map = null; });
    markers = [];
    currentGeodata = geodata;

    if (!geodata.length) {
        if (deckOverlay) deckOverlay.setProps({ layers: [] });
        return;
    }

    // Create markers (hidden initially if zoomed out)
    const showMarkers = map.getZoom() >= 8;

    geodata.forEach(d => {
        const markerEl = createMarkerElement(d.request_count);

        const marker = new google.maps.marker.AdvancedMarkerElement({
            position: { lat: d.lat, lng: d.lng },
            map: showMarkers ? map : null,
            title: `${d.city} — ${d.request_count.toLocaleString()} requests`,
            content: markerEl,
        });

        marker.addListener('click', () => {
            infoWindow.setContent(`
                <div class="iw">
                    <div class="iw-city">${d.city}, ${d.country_code}</div>
                    <div class="iw-count">${d.request_count.toLocaleString()}</div>
                    <div class="iw-detail">
                        <span>${d.ip}</span><br>
                        ${d.lat.toFixed(4)}, ${d.lng.toFixed(4)}
                    </div>
                </div>
            `);
            infoWindow.open(map, marker);
        });

        markers.push({ marker, data: d });
    });

    // Set up deck.gl heatmap
    updateVisibility();

    // Fit bounds with padding for floating panels
    if (geodata.length > 1) {
        const bounds = new google.maps.LatLngBounds();
        geodata.forEach(d => bounds.extend({ lat: d.lat, lng: d.lng }));
        const isMobile = window.innerWidth <= 768;
        map.fitBounds(bounds, isMobile
            ? { top: 80, right: 20, bottom: 100, left: 20 }
            : { top: 80, right: 380, bottom: 100, left: 60 }
        );
    } else if (geodata.length === 1) {
        map.setCenter({ lat: geodata[0].lat, lng: geodata[0].lng });
        map.setZoom(8);
    }
}


function panTo(lat, lng) {
    map.panTo({ lat, lng });
    map.setZoom(10);
    // Close bottom sheet on mobile
    if (window.innerWidth <= 768) {
        document.getElementById('bottom-sheet').classList.remove('open');
        document.getElementById('sheet-backdrop').classList.remove('open');
    }
}
