# Maschine Mikro MK3 — Примеры

Простые примеры для изучения работы с контроллером.

## 📚 Примеры

### simple_monitor.py

Минимальный мониторинг пэдов без LED.

```bash
python examples/simple_monitor.py
```

**Хорош для:**
- Изучения основ
- Старта своих проектов
- Понимания минимальных требований

---

### led_demo.py

Демонстрация всех 17 цветов и 3 уровней яркости.

```bash
python examples/led_demo.py
```

**Хорош для:**
- Понимания цветовой палитры
- Тестирования LED
- Изучения LED протокола

---

## 🚀 Запуск

```bash
# 1. Активируй venv
cd /path/to/maschine
source venv/bin/activate

# 2. Убей NI Agent
killall NIHardwareAgent

# 3. Запусти пример
python examples/simple_monitor.py
```

---

## 🛠️ Создание своих скриптов

Шаблон:

```python
#!/usr/bin/env python3
"""Описание скрипта"""

from maschine import find_devices, Color

def main():
    # Найти устройства
    devices = find_devices(max_count=4)
    if not devices:
        print("Устройства не найдены")
        return

    device = devices[0]
    print(f"Подключено: {device.serial}")

    # Твой код здесь
    device.set_all_pads(Color.CYAN)

    # Закрытие
    device.close()

if __name__ == "__main__":
    main()
```

---

## 📖 Далее

После изучения примеров смотри:

- `midi_bridge.py` — MIDI контроллер
- `PROTOCOL.md` — документация протокола
- Основной `README.md`
