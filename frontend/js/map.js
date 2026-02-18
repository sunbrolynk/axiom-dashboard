/**
 * Google Maps — heatmap, markers, and dark styling.
 *
 * Exports: initMap(), renderMap(geodata), panTo(lat, lng)
 *
 * Zoom-level strategy:
 *   < 8  → HeatmapLayer (density blobs)
 *   >= 8 → Individual circle markers with click info windows
 */

/* global google */

let map, heatmap, infoWindow;
let markers = [];

// Dark map styling
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

const HEATMAP_GRADIENT = [
    'rgba(0, 0, 0, 0)',
    'rgba(99, 102, 241, 0.2)',
    'rgba(99, 102, 241, 0.4)',
    'rgba(139, 92, 246, 0.6)',
    'rgba(168, 85, 247, 0.7)',
    'rgba(236, 72, 153, 0.8)',
    'rgba(239, 68, 68, 0.9)',
    'rgba(255, 255, 255, 1)',
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
    });

    infoWindow = new google.maps.InfoWindow();

    // Switch between heatmap and markers based on zoom level
    map.addListener('zoom_changed', () => {
        const zoom = map.getZoom();
        if (heatmap) heatmap.setMap(zoom < 8 ? map : null);
        markers.forEach(m => m.setMap(zoom >= 8 ? map : null));
    });

    // Trigger initial data load (defined in app.js)
    loadData();
}


function renderMap(geodata) {
    // Clear existing layers
    markers.forEach(m => m.setMap(null));
    markers = [];
    if (heatmap) heatmap.setMap(null);
    if (!geodata.length) return;

    // Heatmap layer
    const heatmapData = geodata.map(d => ({
        location: new google.maps.LatLng(d.lat, d.lng),
        weight: d.request_count,
    }));

    heatmap = new google.maps.visualization.HeatmapLayer({
        data: heatmapData,
        map: map.getZoom() < 8 ? map : null,
        radius: 50,
        opacity: 0.75,
        gradient: HEATMAP_GRADIENT,
    });

    // Individual markers
    geodata.forEach(d => {
        const marker = new google.maps.Marker({
            position: { lat: d.lat, lng: d.lng },
            map: map.getZoom() >= 8 ? map : null,
            title: `${d.city} — ${d.request_count.toLocaleString()} requests`,
            icon: {
                path: google.maps.SymbolPath.CIRCLE,
                scale: Math.max(8, Math.log2(d.request_count + 1) * 3.5),
                fillColor: '#6366f1',
                fillOpacity: 0.85,
                strokeColor: '#a5b4fc',
                strokeWeight: 2,
            },
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

        markers.push(marker);
    });

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
