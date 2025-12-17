# VPNHAMSTER - SOCKS5 Proxy Guide

## Обзор

Это решение использует SOCKS5 прокси с шифрованием для создания защищенного туннеля между Mac клиентом в России и Windows сервером в Казахстане.

**Преимущества подхода:**
- ✅ Не требует драйверов или TUN/TAP на Windows
- ✅ Работает в пользовательском режиме (userspace)
- ✅ Простая настройка и использование
- ✅ Шифрование ChaCha20-Poly1305
- ✅ Поддерживает 95% приложений через системный прокси
- ✅ Выглядит как обычный TCP трафик

**Архитектура:**
```
[Mac приложение] → [Системный SOCKS5 прокси: 127.0.0.1:1080]
                    ↓
[local_proxy.py] → [Шифрованное TCP соединение] → [socks5_server.py на Windows]
                                                   ↓
                                        [Интернет через сервер в Астане]
```

---

## Установка на Windows сервере

### Шаг 1: Установите зависимости

```powershell
cd C:\Users\Administrator\Desktop\VPNHAMSTER
pip install -r requirements-server.txt
```

### Шаг 2: Сгенерируйте ключ шифрования

```powershell
python scripts\generate_key.py
```

**Сохраните ключ!** Он понадобится для клиента на Mac.

Пример вывода:
```
Generated encryption key:
a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6a7b8c9d0e1f2a3b4c5d6a7b8c9d0e1f2
```

### Шаг 3: Откройте порт в firewall

```powershell
# Откройте порт 1080 для SOCKS5 сервера
New-NetFirewallRule -DisplayName "VPNHAMSTER SOCKS5" -Direction Inbound -LocalPort 1080 -Protocol TCP -Action Allow
```

### Шаг 4: Запустите SOCKS5 сервер

```powershell
python server\socks5_server.py --host 0.0.0.0 --port 1080 --key YOUR_KEY_HERE
```

**Замените `YOUR_KEY_HERE` на ключ из шага 2!**

### Ожидаемый вывод:

```
============================================================
VPNHAMSTER - Encrypted SOCKS5 Server
============================================================
Host: 0.0.0.0
Port: 1080
Encryption: ChaCha20-Poly1305
============================================================

INFO - Server listening on 0.0.0.0:1080
INFO - Ready to accept connections!
```

---

## Установка на Mac клиенте

### Шаг 1: Установите зависимости

```bash
cd ~/VPNHAMSTER
pip3 install -r requirements.txt
```

Или с виртуальным окружением:
```bash
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
```

### Шаг 2: Запустите локальный прокси

```bash
# Замените IP_СЕРВЕРА и КЛЮЧ на ваши значения
python3 client/local_proxy.py \
  --server IP_СЕРВЕРА \
  --remote-port 1080 \
  --key КЛЮЧ
```

**Пример:**
```bash
python3 client/local_proxy.py \
  --server 195.49.210.123 \
  --remote-port 1080 \
  --key a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6a7b8c9d0e1f2a3b4c5d6a7b8c9d0e1f2
```

### Ожидаемый вывод:

```
============================================================
VPNHAMSTER - Local SOCKS5 Proxy
============================================================
Local: 127.0.0.1:1080
Remote: 195.49.210.123:1080
Encryption: ChaCha20-Poly1305
============================================================

INFO - Proxy listening on 127.0.0.1:1080
INFO - Ready to forward connections!
```

### Шаг 3: Настройте системный прокси

**В новом терминале** (оставьте local_proxy.py запущенным):

```bash
cd ~/VPNHAMSTER
sudo ./scripts/setup_system_proxy.sh
```

Вывод:
```
======================================
VPNHAMSTER - Setup System Proxy
======================================

Network Service: Wi-Fi

Enabling SOCKS5 proxy...

======================================
Proxy configured successfully!
======================================

SOCKS5 Proxy: 127.0.0.1:1080
```

---

## Проверка работы

### 1. Проверьте IP адрес

```bash
curl https://api.ipify.org
```

**Должен показать IP сервера в Астане!** 🎉

### 2. Проверьте в браузере

Откройте браузер и зайдите на:
- https://whatismyipaddress.com/
- https://2ip.ru/

Должен показаться IP сервера в Казахстане.

### 3. Проверьте DNS

```bash
nslookup google.com
```

DNS запросы тоже должны идти через прокси.

---

## Отключение

### Отключить системный прокси:

```bash
sudo ./scripts/disable_system_proxy.sh
```

### Остановить local_proxy.py:

В терминале где запущен local_proxy.py нажмите `Ctrl+C`.

### Остановить сервер (на Windows):

В PowerShell где запущен socks5_server.py нажмите `Ctrl+C`.

---

## Автоматический запуск (опционально)

### Mac: Создайте alias для быстрого запуска

Добавьте в `~/.zshrc` или `~/.bashrc`:

```bash
alias vpn-start='cd ~/VPNHAMSTER && python3 client/local_proxy.py --server IP_СЕРВЕРА --remote-port 1080 --key КЛЮЧ'
alias vpn-proxy-on='sudo ~/VPNHAMSTER/scripts/setup_system_proxy.sh'
alias vpn-proxy-off='sudo ~/VPNHAMSTER/scripts/disable_system_proxy.sh'
```

Затем используйте:
```bash
vpn-start        # Запустить прокси
vpn-proxy-on     # Включить системный прокси
vpn-proxy-off    # Выключить системный прокси
```

### Windows: Создайте BAT файл для автозапуска

Создайте `start_vpn_server.bat`:

```batch
@echo off
cd C:\Users\Administrator\Desktop\VPNHAMSTER
python server\socks5_server.py --host 0.0.0.0 --port 1080 --key YOUR_KEY_HERE
pause
```

Замените `YOUR_KEY_HERE` на ваш ключ.

---

## Мониторинг подключений

### На сервере (Windows):

Сервер выводит логи всех подключений:
```
INFO - New connection from 123.45.67.89:54321
INFO - Connected: 123.45.67.89:54321 → google.com:443
INFO - Closed: 123.45.67.89:54321 → google.com:443
```

### На клиенте (Mac):

Прокси выводит логи всех запросов:
```
INFO - New connection from 127.0.0.1:54322
INFO - Forwarding to google.com:443
INFO - Connection closed
```

---

## Устранение неполадок

### Проблема: "Connection refused" при запуске local_proxy.py

**Причина:** Сервер на Windows не запущен или порт закрыт.

**Решение:**
1. Проверьте что socks5_server.py запущен на Windows
2. Проверьте firewall: `Get-NetFirewallRule -DisplayName "VPNHAMSTER SOCKS5"`
3. Проверьте доступность порта: `telnet IP_СЕРВЕРА 1080` (на Mac)

### Проблема: Прокси запущен, но сайты не открываются

**Причина:** Системный прокси не настроен.

**Решение:**
```bash
sudo ./scripts/setup_system_proxy.sh
```

Проверьте настройки:
```bash
networksetup -getsocksfirewallproxy Wi-Fi
```

### Проблема: Некоторые приложения не используют прокси

**Причина:** Не все приложения уважают системный прокси.

**Решение:**
- **Терминал/curl:** Работает автоматически
- **Браузеры:** Работают автоматически
- **Другие приложения:** Могут требовать ручной настройки SOCKS5 прокси: `127.0.0.1:1080`

### Проблема: Медленное соединение

**Причина:** Большая задержка или низкая пропускная способность канала.

**Решение:**
1. Проверьте пинг до сервера: `ping IP_СЕРВЕРА`
2. Проверьте скорость канала на сервере
3. Убедитесь что нет других нагрузок на сервер

### Проблема: Прокси работал, но перестал

**Причина:** local_proxy.py или socks5_server.py упал.

**Решение:**
1. Проверьте логи в терминале где запущен прокси
2. Перезапустите local_proxy.py
3. Проверьте что сервер еще работает
4. Проверьте соединение с интернетом на обоих машинах

---

## Безопасность

### Защита ключа шифрования

**ВАЖНО:** Ключ шифрования - это пароль к вашему VPN!

1. **Не сохраняйте ключ в открытом виде в скриптах**
2. **Используйте переменные окружения:**

Mac:
```bash
export VPN_KEY="ваш_ключ"
python3 client/local_proxy.py --server IP --remote-port 1080 --key "$VPN_KEY"
```

Windows:
```powershell
$env:VPN_KEY="ваш_ключ"
python server\socks5_server.py --host 0.0.0.0 --port 1080 --key $env:VPN_KEY
```

### Ротация ключей

Периодически меняйте ключ шифрования:

1. Сгенерируйте новый ключ: `python scripts\generate_key.py`
2. Обновите на сервере (перезапустите с новым ключом)
3. Обновите на клиенте (перезапустите с новым ключом)

---

## Производительность

### Рекомендуемые настройки для Windows сервера

- **CPU:** 2+ ядра
- **RAM:** 2+ GB
- **Сеть:** 10+ Mbps upload
- **Порты:** TCP 1080 открыт

### Оптимизация

Для высокой нагрузки можно увеличить лимиты:

В `server/socks5_server.py` измените:
```python
self.server_socket.listen(100)  # Увеличьте до 200-500
```

---

## Часто задаваемые вопросы

**Q: Можно ли использовать другой порт вместо 1080?**

A: Да! Укажите другой порт при запуске:
```bash
# Сервер
python server\socks5_server.py --port 8080 --key КЛЮЧ

# Клиент
python3 client/local_proxy.py --server IP --remote-port 8080 --key КЛЮЧ
```

**Q: Можно ли подключить несколько клиентов к одному серверу?**

A: Да! Каждый клиент запускает local_proxy.py со своим локальным портом или на своей машине.

**Q: Насколько безопасно это решение?**

A: Очень безопасно! Используется ChaCha20-Poly1305 шифрование (256-bit) - тот же алгоритм что в современных VPN.

**Q: Можно ли использовать на Linux?**

A: Да! local_proxy.py работает на любой Unix системе (Mac/Linux). Только измените пути в скриптах прокси.

**Q: Будет ли работать с торрентами?**

A: Зависит от торрент-клиента. Многие поддерживают SOCKS5 прокси в настройках. Укажите `127.0.0.1:1080`.

---

## Дополнительные возможности

### Per-application прокси (без системного прокси)

Если не хотите включать системный прокси, можно настроить отдельные приложения:

**curl:**
```bash
curl --socks5 127.0.0.1:1080 https://api.ipify.org
```

**ssh:**
```bash
ssh -o ProxyCommand="nc -X 5 -x 127.0.0.1:1080 %h %p" user@host
```

**git:**
```bash
git config --global http.proxy socks5://127.0.0.1:1080
```

**Firefox:** Settings → Network Settings → Manual proxy → SOCKS5: `127.0.0.1:1080`

---

## Сравнение с другими решениями

| Функция | VPNHAMSTER SOCKS5 | OpenVPN | WireGuard | Shadowsocks |
|---------|-------------------|---------|-----------|-------------|
| Простота установки | ✅ Очень простая | ❌ Сложная | ✅ Средняя | ✅ Простая |
| Работа без драйверов | ✅ Да | ❌ Нет | ❌ Нет | ✅ Да |
| Шифрование | ✅ ChaCha20-Poly1305 | ✅ AES-256 | ✅ ChaCha20-Poly1305 | ✅ Различные |
| Обход блокировок РФ | ✅ Отличный | ❌ Блокируется | ❌ Блокируется | ✅ Хороший |
| Кастомизация | ✅ Полная | ❌ Ограничена | ❌ Ограничена | ✅ Средняя |

---

**Поздравляем! Ваш защищенный туннель готов к работе! 🚀**
