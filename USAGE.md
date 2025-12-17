# Примеры использования VPNHAMSTER

## Сценарий 1: Первый запуск

### На сервере (Windows в Астане)

```powershell
# 1. Установка
git clone https://github.com/yourusername/VPNHAMSTER.git
cd VPNHAMSTER
.\scripts\setup_windows.ps1

# 2. Генерация ключа
python scripts\generate_key.py

# Вывод:
# ======================================================================
# VPN Tunnel Encryption Key
# ======================================================================
# Generated Key (save this securely):
# a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2
# ======================================================================

# 3. Открыть порт в firewall
New-NetFirewallRule -DisplayName "VPN Tunnel" -Direction Inbound -LocalPort 8888 -Protocol TCP -Action Allow

# 4. Запустить сервер (скопируйте ключ из шага 2)
python server\server.py --key a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2

# Вывод:
# 2025-12-17 10:00:00 - INFO - Starting VPN Tunnel Server on 0.0.0.0:8888
# 2025-12-17 10:00:00 - INFO - TUN interface created: tun0
# 2025-12-17 10:00:00 - INFO - Server listening on 0.0.0.0:8888
```

### На клиенте (Mac)

```bash
# 1. Установка
git clone https://github.com/yourusername/VPNHAMSTER.git
cd VPNHAMSTER
sudo ./scripts/setup_mac.sh

# 2. Подключение (используйте IP вашего сервера и ключ от сервера)
sudo python3 client/client.py \
  --server 195.49.210.123 \
  --key a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2

# Вывод:
# 2025-12-17 10:05:00 - INFO - Starting VPN Tunnel Client
# 2025-12-17 10:05:00 - INFO - TUN interface created: utun3
# 2025-12-17 10:05:00 - INFO - TUN IP: 10.8.0.2
# 2025-12-17 10:05:00 - INFO - Gateway: 10.8.0.1
# 2025-12-17 10:05:01 - INFO - Connecting to 195.49.210.123:8888
# 2025-12-17 10:05:01 - INFO - Connected to server
# 2025-12-17 10:05:01 - INFO - Handshake completed
# 2025-12-17 10:05:01 - INFO - Tunnel is UP - all traffic is now routed through the tunnel
# 2025-12-17 10:05:01 - INFO - Press Ctrl+C to disconnect
```

## Сценарий 2: Проверка работы туннеля

### Проверка IP адреса

```bash
# До подключения
curl https://api.ipify.org
# Вывод: 178.176.XX.XX (ваш IP в РФ)

# После подключения к туннелю
curl https://api.ipify.org
# Вывод: 195.49.210.123 (IP сервера в Астане)
```

### Проверка доступа к заблокированным ресурсам

```bash
# Проверка доступа к Instagram
curl -I https://www.instagram.com

# Проверка YouTube
curl -I https://www.youtube.com

# Ping тест
ping 8.8.8.8
```

## Сценарий 3: Использование с конфигурационным файлом

### Создание конфигурации клиента

```bash
# Скопировать пример
cp config/client.conf.example config/client.conf

# Редактировать конфигурацию
nano config/client.conf
```

Содержимое `config/client.conf`:

```ini
[client]
server = 195.49.210.123
port = 8888
tun_ip = 10.8.0.2
gateway = 10.8.0.1

[encryption]
key = a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2
```

Затем можно использовать более короткую команду (после добавления поддержки конфига в код):

```bash
sudo python3 client/client.py --config config/client.conf
```

## Сценарий 4: Отключение и восстановление

### Корректное отключение

```bash
# В терминале с запущенным клиентом нажмите:
Ctrl+C

# Вывод:
# 2025-12-17 10:30:00 - INFO - Disconnecting...
# 2025-12-17 10:30:00 - INFO - Cleaning up...
# 2025-12-17 10:30:00 - INFO - Restoring original routing...
# 2025-12-17 10:30:00 - INFO - Routing restored
# 2025-12-17 10:30:00 - INFO - Tunnel closed
```

### Проверка восстановления

```bash
# Проверка IP после отключения
curl https://api.ipify.org
# Вывод: 178.176.XX.XX (ваш оригинальный IP)

# Проверка маршрутов
netstat -rn | grep default
```

## Сценарий 5: Мониторинг и отладка

### Просмотр логов сервера

```powershell
# На сервере Windows
python server\server.py --key YOUR_KEY 2>&1 | Tee-Object -FilePath server.log

# Логи сохраняются в файл server.log
```

### Подробные логи клиента

```bash
# Запустить с дебаг логами
sudo python3 client/client.py --server IP --key KEY --verbose
```

### Мониторинг трафика

```bash
# В отдельном терминале на Mac
sudo tcpdump -i utun3 -n

# Вывод:
# 10:15:23.456789 IP 10.8.0.2.54321 > 8.8.8.8.53: UDP, length 29
# 10:15:23.487234 IP 8.8.8.8.53 > 10.8.0.2.54321: UDP, length 45
```

## Сценарий 6: Использование для конкретных приложений

### Telegram

```bash
# 1. Подключиться к туннелю
sudo python3 client/client.py --server IP --key KEY

# 2. Запустить Telegram
# Весь трафик Telegram теперь идет через Астану
```

### Браузер

```bash
# 1. Подключиться к туннелю
sudo python3 client/client.py --server IP --key KEY

# 2. Открыть любой браузер
# Весь браузерный трафик идет через туннель
```

## Сценарий 7: Автоматический запуск при загрузке (Mac)

### Создание launchd службы

```bash
# Создать plist файл
sudo nano /Library/LaunchDaemons/com.vpnhamster.tunnel.plist
```

Содержимое:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.vpnhamster.tunnel</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3</string>
        <string>/path/to/VPNHAMSTER/client/client.py</string>
        <string>--server</string>
        <string>195.49.210.123</string>
        <string>--key</string>
        <string>YOUR_KEY_HERE</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

Загрузить службу:

```bash
sudo launchctl load /Library/LaunchDaemons/com.vpnhamster.tunnel.plist
```

## Сценарий 8: Изменение порта

### На сервере

```powershell
# Использовать нестандартный порт (например, 443 - выглядит как HTTPS)
python server\server.py --port 443 --key YOUR_KEY

# Не забудьте открыть новый порт в firewall
New-NetFirewallRule -DisplayName "VPN Tunnel 443" -Direction Inbound -LocalPort 443 -Protocol TCP -Action Allow
```

### На клиенте

```bash
sudo python3 client/client.py --server IP --port 443 --key KEY
```

## Сценарий 9: Тестирование производительности

### Тест скорости

```bash
# Установить speedtest-cli
pip3 install speedtest-cli

# Тест до подключения
speedtest-cli

# Подключиться к туннелю
sudo python3 client/client.py --server IP --key KEY

# Тест после подключения (в другом терминале)
speedtest-cli
```

### Тест задержки

```bash
# Ping до подключения
ping -c 10 8.8.8.8

# После подключения
ping -c 10 8.8.8.8
```

## Сценарий 10: Несколько пользователей

### Сервер поддерживает несколько клиентов одновременно

```powershell
# На сервере - один раз запустить
python server\server.py --key YOUR_KEY

# Вывод при подключении клиентов:
# 2025-12-17 10:00:00 - INFO - New connection from ('178.176.1.1', 54321)
# 2025-12-17 10:05:00 - INFO - New connection from ('95.84.2.2', 54322)
# 2025-12-17 10:10:00 - INFO - New connection from ('213.87.3.3', 54323)
```

### Каждый клиент подключается отдельно

```bash
# Клиент 1
sudo python3 client/client.py --server IP --key KEY

# Клиент 2 (на другом Mac)
sudo python3 client/client.py --server IP --key KEY
```

## Важные советы

1. **Храните ключ в безопасности** - не коммитьте его в git
2. **Используйте Ctrl+C** для корректного отключения
3. **Проверяйте IP** после подключения: `curl https://api.ipify.org`
4. **Смотрите логи** при проблемах
5. **Убедитесь в правах root** на клиенте (sudo)
6. **Убедитесь в правах администратора** на сервере

## Команды для быстрого доступа

```bash
# Алиасы для .bashrc или .zshrc на Mac
alias vpn-start='sudo python3 /path/to/VPNHAMSTER/client/client.py --server IP --key KEY'
alias vpn-check='curl https://api.ipify.org'

# Использование
vpn-start   # Запустить туннель
vpn-check   # Проверить IP
```
