# Maschine Mikro MK3 Python Driver

Python-драйвер для Native Instruments Maschine Mikro MK3 с поддержкой до 4 устройств одновременно.

## ✨ Возможности

- 🎛️ **Multi-device** — поддержка до 4 контроллеров
- 🎹 **MIDI Bridge** — превращает контроллер в полноценный MIDI-контроллер
- 🌈 **RGB LED** — 17-цветовая палитра с 3 уровнями яркости
- 📺 **OLED экран** — вывод текста и изображений
- 🎮 **Игры** — Memory Match, Whack-a-Mole, Reaction Game
- 💡 **Световые шоу** — анимации, диско-режим, бегущий текст

## 🚀 Быстрый старт

### 1. Клонируй репозиторий

```bash
git clone https://github.com/Andrew8xx8/maschine.git
cd maschine
```

### 2. Создай виртуальное окружение

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# или: venv\Scripts\activate  # Windows
```

### 3. Установи зависимости

```bash
pip install -r requirements.txt
```

### 4. Отключи Native Instruments Agent

```bash
# macOS/Linux
killall NIHardwareAgent

# Или проверь, что он не запущен
ps aux | grep NI
```

### 5. Запусти!

```bash
python midi_bridge.py
```

---

## 📁 Структура проекта

```
maschine/
├── maschine/                   # 📦 Python-пакет (ядро)
│   ├── __init__.py
│   ├── device.py               # Работа с устройством
│   ├── constants.py            # Цвета, константы
│   ├── device_config.py        # Конфигурация устройств
│   ├── screen.py               # OLED экран
│   ├── screen_font.py          # Шрифты для экрана
│   └── midi.py                 # MIDI утилиты
│
├── examples/                   # 📚 Простые примеры
│   ├── simple_monitor.py       # Минимальный мониторинг пэдов
│   └── led_demo.py             # Демо LED палитры
│
├── midi_bridge.py              # 🎹 MIDI контроллер (основной)
├── midi_bridge_async.py        # 🎹 MIDI контроллер (async версия)
│
├── memory_match.py             # 🎮 Игра Memory Match (2 игрока)
├── pvp_whack.py                # 🎮 PvP Whack-a-Mole (2 игрока)
├── reaction_game.py            # 🎮 Игра на реакцию
│
├── disco.py                    # 💡 Диско-режим
├── gydra_show.py               # 💡 GYDRA световое шоу
├── handson_text.py             # 💡 HANDS ON с эффектами
├── pad_animation.py            # 💡 Анимация на 1 устройстве
├── hui_animation.py            # 💡 Синхронная анимация (4 устройства)
├── today_rs_text.py            # 💡 Прокрутка TODAY.RS
├── pad_scroll_vertical.py      # 💡 Вертикальная прокрутка
├── pad_text_display.py         # 💡 Статичный текст на пэдах
│
├── screen_demo.py              # 📺 Демо OLED экрана
├── image_to_screen.py          # 📺 Картинка на экран
├── maschine_logo_screen.py     # 📺 Логотип на экране
│
├── device_setup.py             # ⚙️ Настройка порядка устройств
├── diagnose_device.py          # 🔍 Диагностика устройств
├── maschine_controller.py      # 🔍 Основной контроллер
├── debug_controller.py         # 🔍 Отладка всех элементов
│
├── color_test.py               # 🧪 Тест цветовой палитры
├── color_mapper.py             # 🧪 Маппинг цветов
├── brightness_test.py          # 🧪 Тест яркости
├── pad_feedback_test.py        # 🧪 Тест обратной связи пэдов
│
└── requirements.txt            # 📋 Зависимости
```

---

## 🎹 MIDI Bridge

Превращает Maschine Mikro MK3 в полноценный MIDI-контроллер:

```bash
python midi_bridge.py
```

**Что умеет:**
- Создаёт виртуальный MIDI-порт `Maschine MK3 MIDI`
- Поддержка до 4 контроллеров (каждый на своём MIDI-канале)
- Velocity 0-127
- Латентность < 2ms
- Визуальная обратная связь (пэды светятся при нажатии)

**Подключение в DAW:**
1. Запусти `python midi_bridge.py`
2. В Ableton/FL Studio/Logic выбери MIDI Input: `Maschine MK3 MIDI`
3. Играй!

---

## 🎮 Игры

### Memory Match (2 игрока, 4 устройства)

```bash
python memory_match.py
```

Параллельная игра на память. Каждый игрок на своих 2 устройствах.

### PvP Whack-a-Mole (2 игрока, 4 устройства)

```bash
python pvp_whack.py
```

Соревновательная игра — бей свои цели быстрее соперника!

### Reaction Game (1 игрок)

```bash
python reaction_game.py
```

Тест скорости реакции. 10 раундов.

---

## 💡 Световые шоу

```bash
# Диско-режим (10 эффектов)
python disco.py

# GYDRA шоу
python gydra_show.py

# HANDS ON с эффектами
python handson_text.py

# Анимация на 1 устройстве
python pad_animation.py

# Синхронная анимация (4 устройства)
python hui_animation.py

# Бегущий текст
python pad_text_display.py "HELLO"
python pad_scroll_vertical.py
```

---

## ⚙️ Настройка нескольких устройств

Если у тебя несколько контроллеров, настрой их порядок один раз:

```bash
python device_setup.py
```

Программа подсветит каждый контроллер и спросит, какой номер присвоить. Настройка сохранится в `~/.maschine_device_config.json`.

📖 Подробнее: [DEVICE_SETUP_GUIDE.md](DEVICE_SETUP_GUIDE.md)

---

## 🔧 Для разработчиков

### Использование как библиотеки

```python
from maschine import MaschineDevice, find_devices, Color

# Найти устройства
devices = find_devices(max_count=4)

# Управление LED
devices[0].set_pad_light(0, Color.RED)
devices[0].set_all_pads(Color.BLUE)
devices[0].clear()

# Чтение событий
pressed = devices[0].read_pads(timeout_ms=10)

# Закрытие
for d in devices:
    d.close()
```

### Простые примеры

```bash
# Минимальный мониторинг пэдов
python examples/simple_monitor.py

# Демо всех 17 цветов
python examples/led_demo.py
```

---

## 📚 Документация

| Документ | Описание |
|----------|----------|
| [PROTOCOL.md](PROTOCOL.md) | HID протокол MK3 |
| [SCREEN_PROTOCOL.md](SCREEN_PROTOCOL.md) | Протокол OLED экрана |
| [BUTTON_LED_MAP.md](BUTTON_LED_MAP.md) | Карта кнопок и LED |
| [ENCODER_PROTOCOL.md](ENCODER_PROTOCOL.md) | Протокол энкодера |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Архитектура системы |
| [DEVICE_SETUP_GUIDE.md](DEVICE_SETUP_GUIDE.md) | Настройка устройств |

---

## 🛠️ Troubleshooting

### Устройства не найдены

```bash
# Убей NI Agent
killall NIHardwareAgent

# Linux: добавь udev правило
echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="17cc", ATTR{idProduct}=="1700", MODE="0666"' | \
  sudo tee /etc/udev/rules.d/50-maschine.rules
sudo udevadm control --reload-rules
```

### Ошибки прав доступа

```bash
# macOS — попробуй с sudo
sudo python midi_bridge.py
```

### LED не работают

Запусти тест:
```bash
python color_test.py
```

---

## 📋 Требования

- Python 3.9+
- macOS / Linux / Windows
- Maschine Mikro MK3

**Зависимости** (`requirements.txt`):
```
hidapi>=0.14.0
Pillow>=10.0.0
python-rtmidi>=1.5.0
```

---

## 🙏 Благодарности

- [r00tman/maschine-mikro-mk3-driver](https://github.com/r00tman/maschine-mikro-mk3-driver) — Rust драйвер MK3
- [wrl/maschine.rs](https://github.com/wrl/maschine.rs) — MK2 драйвер
- Сообщество reverse engineering (cabl, Rebellion, maschinio)

---

## 📄 Лицензия

MIT License

---

**Status:** ✅ Работает — пэды, LED, экран, MIDI
