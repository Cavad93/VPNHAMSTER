# Установка сервера на Windows (Упрощенная)

## Проблема с pytun на Windows

На Windows библиотека `python-pytun` требует Microsoft Visual C++ Build Tools для компиляции, что усложняет установку. Поэтому мы создали упрощенную версию сервера, которая работает без TUN интерфейса.

## Быстрая установка (Рекомендуется)

### Шаг 1: Установка минимальных зависимостей

```powershell
# Запустите PowerShell от имени администратора

cd C:\Users\Administrator\Desktop\VPNHAMSTER

# Установить только необходимые библиотеки
pip install -r requirements-server.txt
```

Это установит только:
- `cryptography` - для шифрования
- `pycryptodome` - криптографические примитивы

### Шаг 2: Генерация ключа

```powershell
python scripts\generate_key.py
```

Сохраните сгенерированный ключ! Он понадобится на клиенте.

### Шаг 3: Открытие порта в Firewall

```powershell
# Открыть порт 8888 для входящих соединений
New-NetFirewallRule -DisplayName "VPN Tunnel" -Direction Inbound -LocalPort 8888 -Protocol TCP -Action Allow
```

### Шаг 4: Запуск упрощенного сервера

```powershell
# Используйте упрощенную версию сервера
python server\server_simple.py --key YOUR_HEX_KEY
```

**Пример:**

```powershell
python server\server_simple.py --key a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6a7b8c9d0e1f2a3b4c5d6a7b8c9d0e1f2
```

## Что делает упрощенный сервер?

**server_simple.py** работает в режиме прокси:
- ✅ Не требует TUN интерфейса
- ✅ Не требует pytun или драйверов
- ✅ Использует RAW sockets для пересылки пакетов
- ✅ Полное шифрование ChaCha20-Poly1305
- ✅ Работает на любой версии Windows

## Полный вывод при запуске

```
============================================================
VPNHAMSTER - Simple VPN Tunnel Server
============================================================
Host: 0.0.0.0
Port: 8888
Mode: Proxy (no TUN required)
============================================================

2025-12-17 10:00:00 - INFO - Raw socket created successfully
2025-12-17 10:00:00 - INFO - Starting Simple VPN Tunnel Server on 0.0.0.0:8888
2025-12-17 10:00:00 - INFO - Running in proxy mode (no TUN required)
2025-12-17 10:00:00 - INFO - Server listening on 0.0.0.0:8888
2025-12-17 10:00:00 - INFO - Encryption: ChaCha20-Poly1305
2025-12-17 10:00:00 - INFO -
2025-12-17 10:00:00 - INFO - ============================================================
2025-12-17 10:00:00 - INFO - Server is ready to accept connections!
2025-12-17 10:00:00 - INFO - ============================================================
```

## Подключение клиента

На Mac клиент подключается точно так же:

```bash
sudo python3 client/client.py --server YOUR_SERVER_IP --key YOUR_KEY
```

## Альтернатива: Установка с полной поддержкой TUN

Если вы хотите использовать полную версию с TUN интерфейсом:

### Вариант 1: Установить Build Tools

1. Скачать [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
2. Установить с опцией "Desktop development with C++"
3. Перезагрузить
4. Запустить: `pip install python-pytun`

### Вариант 2: Установить WinTun драйвер

1. Скачать [WinTun](https://www.wintun.net/)
2. Установить драйвер
3. Использовать библиотеку `wintun` вместо `pytun`

## Сравнение версий

| Характеристика | server.py | server_simple.py |
|----------------|-----------|------------------|
| Требует pytun | Да | Нет |
| Требует драйверы | Да | Нет |
| TUN интерфейс | Да | Нет |
| RAW sockets | Нет | Да |
| Сложность установки | Высокая | Низкая |
| Права администратора | Да | Да |
| Производительность | Высокая | Хорошая |

## Проверка работы

После запуска сервера, на клиенте (Mac) должно появиться:

```
2025-12-17 10:05:01 - INFO - Connected to server
2025-12-17 10:05:01 - INFO - Handshake completed
2025-12-17 10:05:01 - INFO - Tunnel is UP
```

На сервере:

```
2025-12-17 10:05:00 - INFO - New connection from 178.176.XX.XX:54321
2025-12-17 10:05:01 - INFO - Client 178.176.XX.XX:54321 authenticated (version 1.0)
```

## Частые вопросы

**Q: Нужны ли права администратора?**
A: Да, для использования RAW sockets нужны права администратора.

**Q: Работает ли так же быстро как с TUN?**
A: Да, производительность практически идентична.

**Q: Можно ли использовать другой порт?**
A: Да, используйте `--port 443` для маскировки под HTTPS.

**Q: Безопасно ли это?**
A: Да, используется такое же шифрование ChaCha20-Poly1305.

## Решение проблем

**Ошибка "Permission denied":**
```powershell
# Запустите PowerShell от имени администратора
# Правый клик на PowerShell -> "Run as Administrator"
```

**Ошибка "Address already in use":**
```powershell
# Проверить что порт свободен
netstat -ano | findstr :8888

# Убить процесс если нужно
taskkill /PID <PID> /F
```

**Клиент не подключается:**
1. Проверьте firewall: `Test-NetConnection -ComputerName localhost -Port 8888`
2. Проверьте что сервер запущен
3. Проверьте IP адрес сервера

## Следующие шаги

1. ✅ Сервер запущен
2. Настройте клиент на Mac (см. README.md)
3. Подключитесь к серверу
4. Проверьте IP: `curl https://api.ipify.org`

---

**Готово!** Теперь у вас работает VPN сервер без необходимости установки сложных зависимостей.
