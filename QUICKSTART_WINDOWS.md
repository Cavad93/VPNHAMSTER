# Быстрый старт на Windows (ИСПРАВЛЕНО)

## Проблема

При установке `pip install -r requirements.txt` возникает ошибка:
```
error: Microsoft Visual C++ 14.0 or greater is required
```

## Решение

Используйте упрощенную версию сервера без pytun!

## Установка за 3 шага

### 1. Установить минимальные зависимости

```powershell
# В PowerShell от администратора
cd C:\Users\Administrator\Desktop\VPNHAMSTER
pip install -r requirements-server.txt
```

✅ Это установит только `cryptography` и `pycryptodome` - без проблем!

### 2. Сгенерировать ключ

```powershell
python scripts\generate_key.py
```

Скопируйте и сохраните ключ!

### 3. Запустить сервер

```powershell
# Открыть порт
New-NetFirewallRule -DisplayName "VPN" -Direction Inbound -LocalPort 8888 -Protocol TCP -Action Allow

# Запустить УПРОЩЕННЫЙ сервер (вставьте ваш ключ)
python server\server_simple.py --key YOUR_KEY_HERE
```

## Готово!

Вы должны увидеть:

```
============================================================
VPNHAMSTER - Simple VPN Tunnel Server
============================================================
Host: 0.0.0.0
Port: 8888
Mode: Proxy (no TUN required)
============================================================

INFO - Server is ready to accept connections!
```

## На Mac клиенте

```bash
sudo python3 client/client.py --server YOUR_WINDOWS_IP --key YOUR_KEY
```

## Почему это работает?

- **server_simple.py** = Упрощенная версия без TUN
- ❌ Не нужен pytun
- ❌ Не нужен Visual C++
- ❌ Не нужны драйверы
- ✅ Работает сразу
- ✅ Такое же шифрование
- ✅ Та же безопасность

Подробнее: [WINDOWS_SETUP.md](WINDOWS_SETUP.md)
