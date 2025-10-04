document.addEventListener('DOMContentLoaded', () => {
    // --- ELEMENTOS ---
    const resultsDiv = document.getElementById('results');
    const manualLatInput = document.getElementById('manual-lat');
    const manualLonInput = document.getElementById('manual-lon');
    const manualDateInput = document.getElementById('manual-date');

    // --- MAPA LEAFLET ---
    const map = L.map('map').setView([-9.9, -76.2], 5);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
    }).addTo(map);
    let marker = null;

    // ==============================================================================
    // === NUEVA SECCIÓN: Evento de clic en el mapa ===
    // ==============================================================================
    map.on('click', function(e) {
        const lat = e.latlng.lat;
        const lon = e.latlng.lng;

        // 1. Actualiza los campos de texto del formulario con las nuevas coordenadas.
        manualLatInput.value = lat.toFixed(5); // .toFixed(5) para limitar los decimales
        manualLonInput.value = lon.toFixed(5);

        // 2. Mueve el marcador a la ubicación del clic.
        if (marker) {
            map.removeLayer(marker);
        }
        marker = L.marker([lat, lon]).addTo(map);
    });


    // --- FUNCIONES ---
    function updateUI(data) {
        const { latitude, longitude, date, departamento, pais, prediccion_modelo, temperatura_real } = data;
        
        if (marker) map.removeLayer(marker);
        map.setView([latitude, longitude], 12);
        marker = L.marker([latitude, longitude]).addTo(map)
            .bindPopup(`<b>${departamento}</b><br>Predicción: ${prediccion_modelo}`)
            .openPopup();
            
        resultsDiv.innerHTML = `
            <h2>Resultados para ${departamento}, ${pais}</h2>
            <div class="result-item">Fecha: <span>${date}</span></div>
            <div class="result-item">Predicción del Modelo: <span>${prediccion_modelo}</span></div>
            <div class="result-item">Temperatura Real (Histórica): <span>${temperatura_real}</span></div>
        `;
        resultsDiv.style.display = 'block';
    }

    async function fetchData(lat, lon, date) {
        resultsDiv.innerHTML = `<p>Consultando datos...</p>`;
        resultsDiv.style.display = 'block';

        try {
            const response = await fetch('/api/get_location_data', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ latitude: lat, longitude: lon, date: date }),
            });
            const data = await response.json();
            data.latitude = lat;
            data.longitude = lon;
            data.date = date;
            updateUI(data);
        } catch (error) {
            resultsDiv.innerHTML = `<p>Error: No se pudo conectar con el servidor. ¿Está 'app.py' corriendo?</p>`;
        }
    }

    // --- EVENTOS ---
    document.getElementById('get-location-btn').addEventListener('click', () => {
        if (!navigator.geolocation) return alert('Geolocalización no soportada.');
        navigator.geolocation.getCurrentPosition(pos => {
            const { latitude, longitude } = pos.coords;
            const today = document.getElementById('manual-date').value;
            // Actualiza los campos de texto también con la geolocalización
            manualLatInput.value = latitude.toFixed(5);
            manualLonInput.value = longitude.toFixed(5);
            fetchData(latitude, longitude, today);
        }, err => alert(`Error de geolocalización: ${err.message}`));
    });

    document.getElementById('get-manual-btn').addEventListener('click', () => {
        const lat = parseFloat(manualLatInput.value);
        const lon = parseFloat(manualLonInput.value);
        const date = manualDateInput.value;
        if (isNaN(lat) || isNaN(lon) || !date) {
            return alert('Por favor, ingresa latitud, longitud y fecha válidas.');
        }
        fetchData(lat, lon, date);
    });

    // Pone la fecha de hoy por defecto
    document.getElementById('manual-date').value = new Date().toISOString().split('T')[0];
});