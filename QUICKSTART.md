# Быстрый старт VPNHAMSTER

## За 5 минут до работающего туннеля

### На сервере (Windows в Астане)

```powershell
# 1. Скачать проект
git clone https://github.com/yourusername/VPNHAMSTER.git
cd VPNHAMSTER

# 2. Установить зависимости (PowerShell от администратора)
pip install -r requirements.txt

# 3. Сгенерировать ключ
python scripts\generate_key.py
# СОХРАНИТЕ КЛЮЧ! Он понадобится на клиенте

# 4. Открыть порт в firewall
New-NetFirewallRule -DisplayName "VPN" -Direction Inbound -LocalPort 8888 -Protocol TCP -Action Allow

# 5. Запустить сервер (вставьте ваш ключ)
python server\server.py --key YOUR_KEY_HERE
```

### На клиенте (Mac)

```bash
# 1. Скачать проект
git clone https://github.com/yourusername/VPNHAMSTER.git
cd VPNHAMSTER

# 2. Установить зависимости
sudo pip3 install -r requirements.txt

# 3. Подключиться (вставьте IP сервера и ключ от сервера)
sudo python3 client/client.py --server SERVER_IP --key SERVER_KEY
```

## Проверка работы

```bash
# Проверить IP (должен показать IP сервера в Астане)
curl https://api.ipify.org

# Открыть любой заблокированный сайт
# Весь трафик теперь идет через Астану!
```

## Отключение

```bash
# В терминале с клиентом нажать:
Ctrl+C
```

## Что дальше?

- Полная документация: [README.md](README.md)
- Примеры использования: [USAGE.md](USAGE.md)
- Технические детали: [TECHNICAL.md](TECHNICAL.md)

## Частые проблемы

**"Permission denied"** → Используйте `sudo` на клиенте

**Не подключается** → Проверьте firewall на сервере

**Нет интернета** → Проверьте логи сервера

## Помощь

Проблемы? → Откройте issue на GitHub
