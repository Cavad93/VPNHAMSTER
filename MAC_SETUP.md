# Установка клиента на Mac (ИСПРАВЛЕНО)

## Проблема

При установке `pip3 install -r requirements.txt` возникает ошибка:
```
fatal error: 'linux/if_tun.h' file not found
```

Библиотека `python-pytun` не поддерживает macOS.

## Решение

Используйте `pytun-pmd3` - форк с поддержкой macOS!

## Установка на Mac

### Шаг 1: Обновите репозиторий

```bash
cd ~/путь/к/VPNHAMSTER
git pull origin claude/remote-ip-connection-voDcB
```

### Шаг 2: Установите зависимости

```bash
# Используйте -H flag с sudo для правильной установки
sudo -H pip3 install -r requirements.txt
```

Или без sudo (в виртуальное окружение):

```bash
# Создать виртуальное окружение
python3 -m venv venv

# Активировать
source venv/bin/activate

# Установить зависимости
pip3 install -r requirements.txt
```

### Шаг 3: Получите ключ от сервера

Запросите у администратора Windows сервера ключ шифрования.

### Шаг 4: Запустите клиент

```bash
# С sudo (если установили глобально)
sudo python3 client/client.py --server IP_СЕРВЕРА --key КЛЮЧ

# Или из виртуального окружения
source venv/bin/activate
sudo -E python3 client/client.py --server IP_СЕРВЕРА --key КЛЮЧ
```

**Пример:**

```bash
sudo python3 client/client.py \
  --server 195.49.210.123 \
  --key a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6a7b8c9d0e1f2a3b4c5d6a7b8c9d0e1f2
```

## Ожидаемый вывод

```
2025-12-17 10:05:00 - INFO - Starting VPN Tunnel Client
2025-12-17 10:05:00 - INFO - TUN interface created: utun3
2025-12-17 10:05:00 - INFO - TUN IP: 10.8.0.2
2025-12-17 10:05:00 - INFO - Gateway: 10.8.0.1
2025-12-17 10:05:01 - INFO - Connecting to 195.49.210.123:8888
2025-12-17 10:05:01 - INFO - Connected to server
2025-12-17 10:05:01 - INFO - Handshake completed
2025-12-17 10:05:01 - INFO - Setting up routing...
2025-12-17 10:05:01 - INFO - Original gateway: 192.168.1.1
2025-12-17 10:05:01 - INFO - Tunnel is UP - all traffic is now routed through the tunnel
2025-12-17 10:05:01 - INFO - Press Ctrl+C to disconnect
```

## Проверка работы

### Проверить IP адрес

```bash
curl https://api.ipify.org
```

Должен показать IP вашего сервера в Астане!

### Проверить туннель

```bash
# В другом терминале
ifconfig utun3
```

Должен показать интерфейс с IP 10.8.0.2.

## Отключение

В терминале с запущенным клиентом:

```bash
# Нажмите Ctrl+C
# Клиент автоматически восстановит маршруты
```

## Альтернатива: Если pytun-pmd3 не установится

Если и `pytun-pmd3` не работает, используйте встроенный `utun` macOS:

```bash
# Установите только базовые зависимости
pip3 install cryptography pycryptodome
```

Затем я создам упрощенную версию клиента для Mac (сообщите, если понадобится).

## Частые проблемы

**"Permission denied" при создании TUN:**
```bash
# Обязательно используйте sudo
sudo python3 client/client.py ...
```

**Warning о кэше pip:**
```bash
# Это нормально, можете игнорировать
# Или используйте sudo -H
sudo -H pip3 install -r requirements.txt
```

**Xcode Command Line Tools не установлены:**
```bash
xcode-select --install
```

## Быстрая команда (копируй-вставь)

После получения ключа от администратора сервера:

```bash
cd ~/VPNHAMSTER
git pull
sudo -H pip3 install -r requirements.txt
sudo python3 client/client.py --server IP_СЕРВЕРА --key ВАШ_КЛЮЧ
```

---

Готово! Теперь весь ваш трафик идет через сервер в Астане 🚀
