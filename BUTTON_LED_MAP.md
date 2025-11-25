# 🔆 Maschine Mikro MK3 - Button LED Map

Полный маппинг кнопок и их LED индексов на основе официального Rust драйвера.

Источник: `maschine-mikro-mk3-driver/crates/maschine_library/src/controls.rs`

---

## 📋 Структура LED Buffer

```
Байт 0:     0x80 (Report ID)
Байты 1-39: Button LEDs (0x00-0x7f brightness)
Байты 40-55: Pad LEDs (color<<2 | brightness)
Байты 56-79: Slider LEDs (0x00-0x7f brightness)
```

---

## 🔘 Карта кнопок

### Верхние ряды (основные функции)

| LED Index | Кнопка | Описание |
|-----------|--------|----------|
| 0 | MASCHINE | Main Maschine button |
| 1 | STAR | Star/Favorite |
| 2 | BROWSE | Browser |
| 3 | VOLUME | Volume control |

### Второй ряд

| LED Index | Кнопка | Описание |
|-----------|--------|----------|
| 4 | SWING | Swing control |
| 5 | TEMPO | Tempo control |
| 6 | PLUGIN | Plugin mode |
| 7 | SAMPLING | Sampling mode |

### Третий ряд

| LED Index | Кнопка | Описание |
|-----------|--------|----------|
| 8 | LEFT | Navigate left |
| 9 | RIGHT | Navigate right |
| 10 | PITCH | Pitch control |
| 11 | MOD | Modulation control |

### Четвёртый ряд

| LED Index | Кнопка | Описание |
|-----------|--------|----------|
| 12 | PERFORM | Perform mode |
| 13 | NOTES | Notes mode |
| 14 | GROUP | Group button |
| 15 | AUTO | Auto mode |

### Пятый ряд

| LED Index | Кнопка | Описание |
|-----------|--------|----------|
| 16 | LOCK | Lock button |
| 17 | NOTE_REPEAT | Note repeat |
| 18 | RESTART | Restart/Loop |
| 19 | ERASE | Erase |

### Шестой ряд (Transport)

| LED Index | Кнопка | Описание |
|-----------|--------|----------|
| 20 | TAP | Tap tempo |
| 21 | FOLLOW | Follow mode |
| 22 | PLAY | Play ▶️ |
| 23 | REC | Record ⏺️ |

### Седьмой ряд

| LED Index | Кнопка | Описание |
|-----------|--------|----------|
| 24 | STOP | Stop ⏹️ |
| 25 | SHIFT | Shift modifier |
| 26 | FIXED_VEL | Fixed velocity |
| 27 | PAD_MODE | Pad mode selector |

### Восьмой ряд

| LED Index | Кнопка | Описание |
|-----------|--------|----------|
| 28 | KEYBOARD | Keyboard mode |
| 29 | CHORDS | Chords mode |
| 30 | STEP | Step sequencer |
| 31 | SCENE | Scene selection |

### Девятый ряд

| LED Index | Кнопка | Описание |
|-----------|--------|----------|
| 32 | PATTERN | Pattern mode |
| 33 | EVENTS | Events |
| 34 | VARIATION | Variation |
| 35 | DUPLICATE | Duplicate |

### Десятый ряд

| LED Index | Кнопка | Описание |
|-----------|--------|----------|
| 36 | SELECT | Select |
| 37 | SOLO | Solo |
| 38 | MUTE | Mute |

### Encoder (без LED)

| Index | Элемент | LED |
|-------|---------|-----|
| 39 | ENCODER_PRESS | ❌ Нет LED |
| 40 | ENCODER_TOUCH | ❌ Нет LED |

---

## 🎹 MIDI Control Change Map

Для управления из DAW используйте Control Change сообщения:

### Transport Controls
```
CC 22 (PLAY):   0-127 brightness
CC 23 (REC):    0-127 brightness
CC 24 (STOP):   0-127 brightness
CC 20 (TAP):    0-127 brightness
CC 21 (FOLLOW): 0-127 brightness
```

### Mode Selection
```
CC 27 (PAD_MODE): 0-127 brightness
CC 31 (SCENE):    0-127 brightness
CC 32 (PATTERN):  0-127 brightness
CC 28 (KEYBOARD): 0-127 brightness
CC 29 (CHORDS):   0-127 brightness
CC 30 (STEP):     0-127 brightness
```

### Editing
```
CC 36 (SELECT):    0-127 brightness
CC 37 (SOLO):      0-127 brightness
CC 38 (MUTE):      0-127 brightness
CC 35 (DUPLICATE): 0-127 brightness
CC 19 (ERASE):     0-127 brightness
```

### Modifiers
```
CC 25 (SHIFT):      0-127 brightness
CC 26 (FIXED_VEL):  0-127 brightness
CC 17 (NOTE_REPEAT): 0-127 brightness
CC 16 (LOCK):       0-127 brightness
```

---

## 💡 Brightness Levels

Из Rust драйвера (`lights.rs`):

```rust
Brightness::Off = 0x00     // LED выключен
Brightness::Dim = 0x7c     // Тусклый
Brightness::Normal = 0x7e  // Нормальный
Brightness::Bright = 0x7f  // Яркий (максимум)
```

**Рекомендуемые значения:**
- `0x00` - OFF
- `0x2a` - Dim (низкая яркость)
- `0x55` - Normal (средняя яркость)
- `0x7f` - Bright (максимальная яркость)

---

## 🔬 Примеры использования

### Python (прямое управление)

```python
from maschine import find_devices

device = find_devices()[0]

# Включить PLAY button
with device.lock:
    device.led_buffer[1 + 22] = 0x7f  # Index 22 = PLAY, +1 из-за report ID
    device.device.write(device.led_buffer)

# Включить REC button (средняя яркость)
with device.lock:
    device.led_buffer[1 + 23] = 0x55
    device.device.write(device.led_buffer)

# Выключить STOP button
with device.lock:
    device.led_buffer[1 + 24] = 0x00
    device.device.write(device.led_buffer)
```

### MIDI (из DAW)

```
# Включить transport buttons в Ableton/Logic/etc:
Note: Ch1

# PLAY ON
Control Change: CC 22, Value 127

# REC ON
Control Change: CC 23, Value 127

# STOP OFF
Control Change: CC 24, Value 0
```

---

## 🎨 Visual Layout

Физическое расположение кнопок на контроллере (вид сверху):

```
┌───────────────────────────────────────┐
│  [0]  [1]  [2]  [3]    🔍 MASCHINE   │
│                                       │
│  [4]  [5]  [6]  [7]    ⚙️  MODES     │
│                                       │
│  [8]  [9] [10] [11]    ◀️ ▶️  NAV     │
│                                       │
│ [12] [13] [14] [15]    🎵 PERFORM    │
│                                       │
│ [16] [17] [18] [19]    🔒 EDIT       │
│                                       │
│ [20] [21] [22] [23]    ▶️ ⏺️  TRANS   │
│                                       │
│ [24] [25] [26] [27]    ⏹️  CONTROL   │
│                                       │
│ [28] [29] [30] [31]    🎹 MODES 2    │
│                                       │
│ [32] [33] [34] [35]    📋 PATTERN    │
│                                       │
│ [36] [37] [38]         🎚️  MIXER     │
│                                       │
│       [ENCODER 39/40]  (no LED)      │
│                                       │
│  ╔═══╗ ╔═══╗ ╔═══╗ ╔═══╗            │
│  ║ 0 ║ ║ 1 ║ ║ 2 ║ ║ 3 ║            │
│  ╚═══╝ ╚═══╝ ╚═══╝ ╚═══╝            │
│  ╔═══╗ ╔═══╗ ╔═══╗ ╔═══╗            │
│  ║ 4 ║ ║ 5 ║ ║ 6 ║ ║ 7 ║   PADS    │
│  ╚═══╝ ╚═══╝ ╚═══╝ ╚═══╝   40-55    │
│  ╔═══╗ ╔═══╗ ╔═══╗ ╔═══╗            │
│  ║ 8 ║ ║ 9 ║ ║10 ║ ║11 ║            │
│  ╚═══╝ ╚═══╝ ╚═══╝ ╚═══╝            │
│  ╔═══╗ ╔═══╗ ╔═══╗ ╔═══╗            │
│  ║12 ║ ║13 ║ ║14 ║ ║15 ║            │
│  ╚═══╝ ╚═══╝ ╚═══╝ ╚═══╝            │
└───────────────────────────────────────┘
```

---

## 🧪 Тестирование

Используйте `debug_controller.py` для проверки:

```bash
# Тест всех button LED
python3 debug_controller.py

# Выберите опцию 1

# Или напрямую:
python3 debug_controller.py --leds
```

---

## ✅ Проверено

Все индексы взяты из официального Rust драйвера:
- ✅ `maschine-mikro-mk3-driver/crates/maschine_library/src/controls.rs`
- ✅ `maschine-mikro-mk3-driver/crates/maschine_library/src/lights.rs`

**Последнее обновление:** 2025-11-21

