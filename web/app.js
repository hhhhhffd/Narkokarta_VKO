/**
 * Telegram WebApp с картой на базе Leaflet
 *
 * Функции:
 * - Отображение меток на карте с кластеризацией (Leaflet.markercluster)
 * - Просмотр всех общедоступных меток
 * - Создание меток через клик на карту (только тип и геопозиция)
 * - Автоматическое привязывание цветов к типам меток
 * - Интеграция с Telegram WebApp API
 * - Фильтрация меток по типу, цвету и радиусу
 */

// ==================== Конфигурация ====================

const CONFIG = {
    API_BASE_URL: window.location.origin || 'http://localhost:8000',
    TILE_LAYER: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
    TILE_ATTRIBUTION: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    DEFAULT_CENTER: [49.948658972761386, 82.6267031181721], // Астана [lat, lng] для Leaflet
    DEFAULT_ZOOM: 12,
    MIN_DISTANCE_METERS: 5, // Минимальное расстояние между метками
    COLOR_MAP: {
        red: '#dc3545',
        orange: '#fd7e14',
        yellow: '#ffc107',
        green: '#28a745',
        white: '#6c757d',
        purple: '#9b59b6'  // Для кластеров
    },
    TYPE_COLORS: {
        den: 'red',
        ad: 'orange',
        courier: 'yellow',
        user: 'green',
        trash: 'white'
    },
    TYPE_ICONS: {
        den: '🏚',
        ad: '📢',
        courier: '🚶',
        user: '💊',
        trash: '🗑'
    }
};

// ==================== State ====================

const state = {
    map: null,
    markers: [],
    markerClusterGroup: null,
    accessToken: null,
    userInfo: null,
    currentPosition: null,
    tg: null,
    filters: {
        types: ['den', 'ad', 'courier', 'user', 'trash']
    }
};

// ==================== Telegram WebApp ====================

function initTelegram() {
    if (window.Telegram && window.Telegram.WebApp) {
        state.tg = window.Telegram.WebApp;
        state.tg.ready();
        state.tg.expand();

        // Получаем данные пользователя из Telegram
        const user = state.tg.initDataUnsafe?.user;
        if (user) {
            console.log('Telegram user:', user);
            // Здесь можно автоматически авторизовать пользователя
        }

        // Настраиваем кнопку "Закрыть"
        state.tg.BackButton.onClick(() => {
            state.tg.close();
        });
    }
}

// ==================== Утилиты ====================

function calculateDistance(lat1, lon1, lat2, lon2) {
    const R = 6371000; // Радиус Земли в метрах
    const φ1 = lat1 * Math.PI / 180;
    const φ2 = lat2 * Math.PI / 180;
    const Δφ = (lat2 - lat1) * Math.PI / 180;
    const Δλ = (lon2 - lon1) * Math.PI / 180;

    const a = Math.sin(Δφ / 2) * Math.sin(Δφ / 2) +
              Math.cos(φ1) * Math.cos(φ2) *
              Math.sin(Δλ / 2) * Math.sin(Δλ / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

    return R * c;
}

function findNearbyMarker(lat, lon, maxDistance = CONFIG.MIN_DISTANCE_METERS) {
    return state.markers.find(marker => {
        const distance = calculateDistance(lat, lon, marker.latitude, marker.longitude);
        return distance < maxDistance;
    });
}

// ==================== API Client ====================

class API {
    static async request(endpoint, options = {}) {
        const url = `${CONFIG.API_BASE_URL}${endpoint}`;
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };

        if (state.accessToken) {
            headers['Authorization'] = `Bearer ${state.accessToken}`;
        }

        try {
            const response = await fetch(url, {
                ...options,
                headers
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Network error');
            }

            return await response.json();
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    }

    static async requestOTP(phone) {
        return this.request('/auth/request-otp', {
            method: 'POST',
            body: JSON.stringify({ phone })
        });
    }

    static async verifyOTP(phone, code) {
        return this.request('/auth/verify-otp', {
            method: 'POST',
            body: JSON.stringify({ phone, code })
        });
    }

    static async getMarkers(filters = {}) {
        const params = new URLSearchParams(filters);
        return this.request(`/markers?${params}`);
    }

    static async createMarker(data) {
        return this.request('/markers', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    static async uploadPhoto(markerId, file) {
        const formData = new FormData();
        formData.append('photo', file);

        const url = `${CONFIG.API_BASE_URL}/markers/${markerId}/photo`;
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${state.accessToken}`
            },
            body: formData
        });

        if (!response.ok) {
            throw new Error('Upload failed');
        }

        return response.json();
    }

    static async getUserStats() {
        return this.request('/users/me/stats');
    }
}

// ==================== UI Helpers ====================

function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const icons = {
        success: 'fa-check-circle',
        error: 'fa-exclamation-circle',
        info: 'fa-info-circle',
        warning: 'fa-exclamation-triangle'
    };

    toast.innerHTML = `
        <i class="fas ${icons[type]}"></i>
        <span>${message}</span>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

function showLoader() {
    document.getElementById('loader').classList.remove('hidden');
}

function hideLoader() {
    document.getElementById('loader').classList.add('hidden');
}

function openModal(modalId) {
    document.getElementById(modalId).classList.add('active');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
}

// ==================== Map Functions ====================

async function initMap() {
    console.log('Создание карты...');
    try {
        // Создаём карту с Leaflet
        state.map = L.map('map').setView(CONFIG.DEFAULT_CENTER, CONFIG.DEFAULT_ZOOM);

        console.log('✅ Карта создана');

        // Добавляем слой тайлов OpenStreetMap
        L.tileLayer(CONFIG.TILE_LAYER, {
            attribution: CONFIG.TILE_ATTRIBUTION,
            maxZoom: 19
        }).addTo(state.map);

        console.log('✅ Тайлы добавлены');

        // Инициализируем группу кластеризации
        state.markerClusterGroup = L.markerClusterGroup({
            maxClusterRadius: 50,
            spiderfyOnMaxZoom: true,
            showCoverageOnHover: false,
            zoomToBoundsOnClick: true
        });
        state.map.addLayer(state.markerClusterGroup);

        console.log('✅ Кластеризация настроена');

        // Добавляем обработчик клика по карте
        state.map.on('click', handleMapClick);
        console.log('✅ Обработчик клика добавлен');

        // Загружаем метки
        console.log('Загрузка меток...');
        await loadMarkers();
        console.log('✅ Метки загружены');

        // Получаем текущую позицию
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    state.currentPosition = {
                        lat: position.coords.latitude,
                        lng: position.coords.longitude
                    };
                    state.map.flyTo([position.coords.latitude, position.coords.longitude], 13);
                    console.log('✅ Геолокация получена');
                },
                (error) => {
                    console.error('❌ Ошибка геолокации:', error);
                }
            );
        }

        hideLoader();

    } catch (error) {
        console.error('❌ Критическая ошибка при создании карты:', error);
        hideLoader();
        showToast('Не удалось загрузить карту: ' + error.message, 'error');
    }
}

async function loadMarkers() {
    try {
        console.log('Загрузка меток...');

        const filters = {};

        console.log('Запрос меток с фильтрами:', filters);
        const markers = await API.getMarkers(filters);
        console.log(`Получено меток: ${markers.length}`);

        // Фильтруем только по типу на клиенте
        const filteredMarkers = markers.filter(m =>
            state.filters.types.includes(m.type)
        );

        console.log(`После фильтрации: ${filteredMarkers.length}`);

        state.markers = filteredMarkers;
        displayMarkers(filteredMarkers);
        updateStats(filteredMarkers.length);

    } catch (error) {
        console.error('Ошибка загрузки меток:', error);
        showToast('Ошибка загрузки меток: ' + error.message, 'error');
    }
}

function displayMarkers(markers) {
    console.log(`Отображение ${markers.length} меток на карте`);

    // Очищаем старые метки из группы кластеризации
    state.markerClusterGroup.clearLayers();

    // Создаём иконку для каждого типа метки
    const createIcon = (type, color) => {
        const iconEmoji = CONFIG.TYPE_ICONS[type] || '📍';
        const iconColor = CONFIG.COLOR_MAP[CONFIG.TYPE_COLORS[type]] || '#999';

        return L.divIcon({
            html: `<div style="
                background-color: ${iconColor};
                width: 32px;
                height: 32px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 18px;
                border: 2px solid white;
                box-shadow: 0 2px 5px rgba(0,0,0,0.3);
            ">${iconEmoji}</div>`,
            className: 'custom-marker-icon',
            iconSize: [32, 32],
            iconAnchor: [16, 16],
            popupAnchor: [0, -16]
        });
    };

    // Создаём popup для метки
    const createPopup = (marker) => {
        const typeMap = {
            den: '🏚 Притон',
            ad: '📢 Реклама',
            courier: '🚶 Курьер',
            user: '💊 Употребление',
            trash: '🗑 Мусор'
        };

        const statusMap = {
            new: 'Новая',
            approved: 'Одобрена',
            rejected: 'Отклонена',
            resolved: 'Решена'
        };

        return `
            <div class="marker-popup">
                <h3>${marker.title}</h3>
                ${marker.description ? `<p>${marker.description}</p>` : ''}
                <div class="marker-meta">
                    <span class="badge type">${typeMap[marker.type]}</span>
                    <span class="badge status ${marker.status}">${statusMap[marker.status]}</span>
                </div>
                <p><small>📅 ${new Date(marker.created_at).toLocaleString('ru')}</small></p>
                ${marker.photo_url ? `<img src="${CONFIG.API_BASE_URL}${marker.photo_url}" alt="Фото" style="max-width: 100%; margin-top: 10px; border-radius: 5px;">` : ''}
            </div>
        `;
    };

    // Добавляем метки на карту
    markers.forEach(marker => {
        const leafletMarker = L.marker(
            [marker.latitude, marker.longitude],
            { icon: createIcon(marker.type, marker.color) }
        );

        leafletMarker.bindPopup(createPopup(marker), {
            maxWidth: 300,
            className: 'custom-popup'
        });

        state.markerClusterGroup.addLayer(leafletMarker);
    });

    console.log(`✅ Добавлено ${markers.length} меток с кластеризацией`);
}

function updateStats(total) {
    document.getElementById('totalMarkers').textContent = total;
}

// ==================== Auth ====================
// Авторизация происходит только через Telegram WebApp

// ==================== Add Marker ====================

function showAddMarkerModal(lat, lng) {
    document.getElementById('markerLat').textContent = lat.toFixed(6);
    document.getElementById('markerLon').textContent = lng.toFixed(6);
    document.getElementById('markerType').value = 'den';

    // Автоматически заполняем адрес координатами
    document.getElementById('markerAddress').value = `Координаты: ${lat.toFixed(6)}, ${lng.toFixed(6)}`;

    document.getElementById('markerDescription').value = '';
    document.getElementById('markerPhoto').value = '';

    openModal('markerModal');
}

async function handleSubmitMarker() {
    const type = document.getElementById('markerType').value;
    const address = document.getElementById('markerAddress').value.trim();
    const description = document.getElementById('markerDescription').value.trim();
    const lat = parseFloat(document.getElementById('markerLat').textContent);
    const lng = parseFloat(document.getElementById('markerLon').textContent);
    const photoFile = document.getElementById('markerPhoto').files[0];

    // Проверяем близость еще раз перед отправкой
    const nearbyMarker = findNearbyMarker(lat, lng);
    if (nearbyMarker) {
        showToast(`Слишком близко к существующей метке (${CONFIG.MIN_DISTANCE_METERS}м)`, 'warning');
        return;
    }

    try {
        showLoader();

        // Создаём метку с адресом и опциональным описанием
        const markerData = {
            latitude: lat,
            longitude: lng,
            type
        };

        // Добавляем адрес если заполнен
        if (address) {
            markerData.address = address;
        }

        // Добавляем описание если заполнено
        if (description) {
            markerData.description = description;
        }

        const marker = await API.createMarker(markerData);

        // Загружаем фото если есть
        if (photoFile) {
            try {
                await API.uploadPhoto(marker.id, photoFile);
                showToast('Метка создана с фото и опубликована!', 'success');
            } catch (error) {
                console.error('Ошибка загрузки фото:', error);
                showToast('Метка создана, но фото не загружено', 'warning');
            }
        } else {
            showToast('Метка создана и опубликована на карте!', 'success');
        }

        closeModal('markerModal');

        // Перезагружаем метки на карте
        await loadMarkers();

    } catch (error) {
        console.error('Ошибка создания метки:', error);
        showToast('Ошибка создания метки: ' + error.message, 'error');
    } finally {
        hideLoader();
    }
}

function handleMapClick(e) {
    // Открываем модальное окно создания метки только если авторизован
    if (state.accessToken) {
        const lat = e.latlng.lat;
        const lng = e.latlng.lng;

        // Проверяем близость к существующим меткам
        const nearbyMarker = findNearbyMarker(lat, lng);
        if (nearbyMarker) {
            showToast(`Слишком близко к существующей метке (${CONFIG.MIN_DISTANCE_METERS}м)`, 'warning');
            return;
        }

        showAddMarkerModal(lat, lng);
    }
}

// ==================== Filters ====================

function applyFilters() {
    // Собираем выбранные типы
    const typeCheckboxes = document.querySelectorAll('input[name="type"]:checked');
    state.filters.types = Array.from(typeCheckboxes).map(cb => cb.value);

    loadMarkers();
    showToast('Фильтры применены', 'success');
}

function resetFilters() {
    // Сбрасываем все чекбоксы типов
    document.querySelectorAll('input[name="type"]').forEach(cb => cb.checked = true);

    state.filters = {
        types: ['den', 'ad', 'courier', 'user', 'trash']
    };

    loadMarkers();
    showToast('Фильтры сброшены', 'info');
}

// ==================== Event Listeners ====================

function initEventListeners() {
    // Modals
    document.querySelectorAll('.modal-close').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const modal = e.target.closest('.modal');
            modal.classList.remove('active');
        });
    });

    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.remove('active');
            }
        });
    });

    // Add Marker (доступно через клик на карту для авторизованных в Telegram)
    document.getElementById('submitMarker').addEventListener('click', handleSubmitMarker);

    // Filters
    document.getElementById('applyFilters').addEventListener('click', applyFilters);
    document.getElementById('resetFilters').addEventListener('click', resetFilters);

    // Sidebar
    document.getElementById('toggleSidebar').addEventListener('click', () => {
        document.getElementById('sidebar').classList.toggle('closed');
    });
    document.getElementById('closeSidebar').addEventListener('click', () => {
        document.getElementById('sidebar').classList.add('closed');
    });

    // My Location
    document.getElementById('myLocation').addEventListener('click', () => {
        if (state.currentPosition) {
            state.map.flyTo([state.currentPosition.lat, state.currentPosition.lng], 15);
        } else {
            showToast('Геолокация недоступна', 'warning');
        }
    });
}

// ==================== Initialization ====================

async function init() {
    console.log('🚀 Инициализация WebApp...');
    console.log('API URL:', CONFIG.API_BASE_URL);

    try {
        // Инициализируем Telegram WebApp
        console.log('1/4 Инициализация Telegram...');
        initTelegram();

        // Получаем токен из Telegram WebApp initData
        console.log('2/4 Получение токена из Telegram...');
        if (state.tg && state.tg.initData) {
            // Здесь будет логика получения токена от бэкенда на основе Telegram initData
            console.log('✅ Telegram WebApp данные получены');
        }

        // Инициализируем карту
        console.log('3/4 Инициализация карты...');
        await initMap();

        // Инициализируем обработчики
        console.log('4/4 Инициализация обработчиков...');
        initEventListeners();

        setTimeout(hideLoader, 500);

        console.log('✅ Инициализация завершена!');
    } catch (error) {
        console.error('❌ Ошибка инициализации:', error);
        hideLoader();
        showToast('Ошибка загрузки приложения: ' + error.message, 'error');
    }
}

// Запуск при загрузке страницы
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
