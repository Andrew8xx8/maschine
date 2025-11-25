# 🏗️ Архитектура системы Maschine MK3

**Версия:** 1.0
**Дата:** November 21, 2025

---

## 📋 Оглавление

1. [Обзор системы](#обзор-системы)
2. [Архитектурные слои](#архитектурные-слои)
3. [Основные компоненты](#основные-компоненты)
4. [Потоки данных](#потоки-данных)
5. [Жизненный цикл устройства](#жизненный-цикл-устройства)
6. [Конфигурация устройств](#конфигурация-устройств)
7. [Паттерны взаимодействия](#паттерны-взаимодействия)
8. [Производительность](#производительность)

---

## 🎯 Обзор системы

### Цель

Предоставить единую, простую и производительную систему для работы с несколькими контроллерами Maschine Mikro MK3.

### Принципы

1. **DRY (Don't Repeat Yourself)** - нет дублирования кода инициализации
2. **Единая точка истины** - конфигурация устройств в одном месте
3. **Plug & Play** - минимальная настройка для начала работы
4. **Производительность** - оптимизированные операции с LED
5. **Наглядность** - визуальная идентификация устройств

---

## 🏛️ Архитектурные слои

```
┌─────────────────────────────────────────────────────────────┐
│                    APPLICATION LAYER                        │
│  (Games, MIDI Bridge, Animations, Utilities)                │
│                                                             │
│  memory_match.py  pvp_whack.py  midi_bridge.py  disco.py   │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │ uses
                            │
┌─────────────────────────────────────────────────────────────┐
│                   MASCHINE MODULE LAYER                     │
│         (High-level API, Device Management)                 │
│                                                             │
│  • setup_devices_with_config()  ← main entry point         │
│  • MaschineDevice class                                     │
│  • Device configuration management                          │
│  • Color/Brightness constants                               │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │ uses
                            │
┌─────────────────────────────────────────────────────────────┐
│                    PROTOCOL LAYER                           │
│       (HID Communication, NHL Handshake)                    │
│                                                             │
│  • NHL Registration                                         │
│  • Wake-up sequences                                        │
│  • LED buffer management                                    │
│  • Pad event decoding                                       │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │ uses
                            │
┌─────────────────────────────────────────────────────────────┐
│                    HARDWARE LAYER                           │
│            (USB HID, Operating System)                      │
│                                                             │
│  • hidapi library                                           │
│  • USB HID protocol                                         │
│  • Maschine Mikro MK3 hardware                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 Основные компоненты

### 1. Модуль `maschine/`

Центральный модуль системы.

```
maschine/
├── __init__.py           # Public API
├── constants.py          # Color palette, event types
├── device.py             # MaschineDevice class
└── device_config.py      # Configuration management
```

#### **`maschine/device.py`**

**Ответственность:**
- Инициализация HID устройств
- NHL handshake протокол
- LED управление (с оптимизацией)
- Чтение pad событий
- Визуальная идентификация

**Ключевые классы:**

```python
class MaschineDevice:
    """Represents a single Maschine Mikro MK3 controller"""

    # Initialization
    def connect() -> bool

    # LED Control
    def set_pad_light(pad_idx, color_idx, brightness, on)
    def set_pattern(pattern, color_idx, brightness)
    def set_all_pads(color_idx, brightness)
    def clear()
    def show_device_number(device_number, color_idx, duration)

    # Input
    def read_pads(timeout_ms) -> List[int]
    def read_pads_with_velocity(timeout_ms) -> List[tuple]

    # Lifecycle
    def close()
```

**Ключевые функции:**

```python
def find_devices(max_count, debug) -> List[MaschineDevice]
    """Find and initialize all connected devices"""

def setup_devices_with_config(max_count, debug, show_numbers, show_duration) -> List[tuple]
    """Main entry point: find, sort, and visually identify devices"""
```

---

#### **`maschine/device_config.py`**

**Ответственность:**
- Сохранение/загрузка конфигурации устройств
- Сортировка устройств по конфигурации
- Управление файлом `~/.maschine_device_config.json`

**Ключевые функции:**

```python
def load_device_config() -> Dict[str, int]
    """Load device configuration from ~/.maschine_device_config.json"""

def save_device_config(config: Dict[str, int]) -> bool
    """Save device configuration"""

def sort_devices_by_config(devices, config) -> List[tuple]
    """Sort devices by saved configuration"""
```

**Формат конфигурации:**

```json
{
  "serial_number_1": 1,  // Device number
  "serial_number_2": 2,
  "serial_number_3": 3,
  "serial_number_4": 4
}
```

---

#### **`maschine/constants.py`**

**Ответственность:**
- Цветовая палитра (17 цветов)
- Уровни яркости (3 уровня)
- Типы pad событий
- HID константы (Vendor ID, Product ID)

**Основные константы:**

```python
class Color:
    OFF = 0
    RED = 1
    ORANGE = 2
    # ... 17 colors total

BRIGHTNESS_OFF = 0x00
BRIGHTNESS_DIM = 0x2a
BRIGHTNESS_NORMAL = 0x55
BRIGHTNESS_BRIGHT = 0x7f

class PadEventType:
    PRESS_ON = 0x00
    NOTE_ON = 0x10
    PRESS_OFF = 0x20
    NOTE_OFF = 0x30
    AFTERTOUCH = 0x40
```

---

### 2. Утилита `device_setup.py`

**Ответственность:**
- Интерактивная настройка порядка устройств
- Визуальная идентификация (1, 2, 3, 4 пэда)
- Сохранение конфигурации

**Использование:**

```bash
python3 device_setup.py        # Настроить порядок
python3 device_setup.py --show # Показать конфигурацию
```

---

### 3. Прикладной слой

**Игры:**
- `memory_match.py` - Memory Match (2 игрока, 4 устройства)
- `pvp_whack.py` - PvP Whack-a-Mole (2 игрока, 4 устройства)
- `reaction_game.py` - Reaction Game (1 игрок, 1-4 устройства)

**Утилиты:**
- `midi_bridge.py` - MIDI контроллер (1-4 устройства)
- `color_test.py` - Тест палитры (1 устройство)
- `pad_animation.py` - Анимации (1 устройство)

**Все используют одинаковый паттерн инициализации.**

---

## 🔄 Потоки данных

### 1. Инициализация устройств

```
┌──────────────────────────────────────────────────────────────┐
│ APPLICATION (memory_match.py, midi_bridge.py, etc.)         │
└────────────────────┬─────────────────────────────────────────┘
                     │
                     │ setup_devices_with_config()
                     ▼
┌──────────────────────────────────────────────────────────────┐
│ maschine/device.py                                           │
│                                                              │
│  1. find_devices()                                           │
│     └─> hid.enumerate() → List[device_info]                 │
│     └─> For each: MaschineDevice(info).connect()            │
│                                                              │
│  2. sort_devices_by_config()                                 │
│     └─> load_device_config() from ~/.maschine...json        │
│     └─> Sort by device_number from config                   │
│                                                              │
│  3. show_device_number() for each                            │
│     └─> Light up 1,2,3,4 pads (Cyan)                        │
│     └─> Visual identification!                               │
│                                                              │
└────────────────────┬─────────────────────────────────────────┘
                     │
                     │ Returns: [(device, device_num), ...]
                     ▼
┌──────────────────────────────────────────────────────────────┐
│ APPLICATION                                                  │
│                                                              │
│  devices = [device for device, _ in sorted_devices]         │
│  # Now devices are in correct order!                        │
└──────────────────────────────────────────────────────────────┘
```

---

### 2. Чтение pad событий

```
┌──────────────────────────────────────────────────────────────┐
│ HARDWARE: User presses pad                                   │
└────────────────────┬─────────────────────────────────────────┘
                     │
                     │ USB HID Report (64 bytes)
                     ▼
┌──────────────────────────────────────────────────────────────┐
│ hidapi: device.read(64, timeout_ms)                          │
└────────────────────┬─────────────────────────────────────────┘
                     │
                     │ Raw HID data
                     ▼
┌──────────────────────────────────────────────────────────────┐
│ MaschineDevice.read_pads() or read_pads_with_velocity()     │
│                                                              │
│  Decode 3-byte triplets:                                     │
│    [pad_idx, event_byte, velocity_low]                       │
│                                                              │
│  event_type = event_byte & 0xf0                              │
│  velocity = ((event_byte & 0x0f) << 8) | velocity_low       │
│                                                              │
└────────────────────┬─────────────────────────────────────────┘
                     │
                     │ List[pad_idx] or List[(pad, vel, type)]
                     ▼
┌──────────────────────────────────────────────────────────────┐
│ APPLICATION: Process events                                  │
│                                                              │
│  for pad in pressed_pads:                                    │
│      handle_pad_press(pad)                                   │
└──────────────────────────────────────────────────────────────┘
```

---

### 3. Управление LED (оптимизированное)

```
┌──────────────────────────────────────────────────────────────┐
│ APPLICATION: Game logic                                      │
│                                                              │
│  device.set_pad_light(0, Color.RED)   # Update buffer       │
│  device.set_pad_light(1, Color.BLUE)  # Update buffer       │
│  device.set_pad_light(2, Color.GREEN) # Update buffer       │
│  # No HID writes yet!                                        │
│                                                              │
└────────────────────┬─────────────────────────────────────────┘
                     │
                     │ Updates internal led_buffer
                     ▼
┌──────────────────────────────────────────────────────────────┐
│ MaschineDevice: LED buffer (81 bytes)                        │
│                                                              │
│  [0x80, ..., PAD_DATA @ offset 40, ...]                      │
│                                                              │
│  buffer_dirty = True                                         │
│                                                              │
└────────────────────┬─────────────────────────────────────────┘
                     │
                     │ Explicit flush or auto-flush
                     ▼
┌──────────────────────────────────────────────────────────────┐
│ MaschineDevice.write_led_buffer()                            │
│  OR set_pad_light(...) with lock                             │
│                                                              │
│  ONE HID write for all changes!                              │
│                                                              │
└────────────────────┬─────────────────────────────────────────┘
                     │
                     │ HID Report (81 bytes)
                     ▼
┌──────────────────────────────────────────────────────────────┐
│ HARDWARE: LEDs light up                                      │
└──────────────────────────────────────────────────────────────┘
```

**Оптимизация:** Множество изменений → один HID write!

---

## 🔄 Жизненный цикл устройства

### Диаграмма состояний

```
┌──────────────┐
│ DISCONNECTED │
└──────┬───────┘
       │
       │ hid.device.open()
       ▼
┌──────────────┐
│   OPENED     │
└──────┬───────┘
       │
       │ NHL Registration (Report 0x03)
       ▼
┌──────────────┐
│ REGISTERED   │
└──────┬───────┘
       │
       │ Wake-up sequences (Reports 0x01, 0x04, 0x80)
       ▼
┌──────────────┐
│ INITIALIZED  │
└──────┬───────┘
       │
       │ set_nonblocking(True)
       ▼
┌──────────────┐
│    READY     │ ◄──────────────┐
└──────┬───────┘                │
       │                        │
       │ Application uses       │
       │ (read/write)           │
       │                        │
       └────────────────────────┘
       │
       │ close()
       ▼
┌──────────────┐
│   CLOSED     │
└──────────────┘
```

### Инициализация (детально)

```python
def connect(self) -> bool:
    # 1. Open HID device
    self.device = hid.device()
    self.device.open_path(self.info['path'])

    # 2. NHL Registration (Native Hardware Library)
    client_id = os.urandom(8)  # Unique ID
    self.device.write([0x03, 0x01] + list(client_id) + [0x00] * 54)
    time.sleep(0.05)

    # 3. Wake-up sequences
    for seq in INIT_SEQUENCES:
        self.device.write(seq)
        time.sleep(0.03)

    # 4. Set non-blocking mode
    self.device.set_nonblocking(True)
    time.sleep(0.1)

    # 5. Clear all LEDs
    self.clear()

    return True
```

---

## ⚙️ Конфигурация устройств

### Файл конфигурации

**Расположение:** `~/.maschine_device_config.json`

**Формат:**

```json
{
  "0001A0B2": 1,
  "0001A177": 2,
  "0001XXXX": 3,
  "0001YYYY": 4
}
```

**Ключ:** Серийный номер устройства (уникальный!)
**Значение:** Номер устройства (1-4)

### Процесс настройки

```
┌──────────────────────────────────────────────────────────────┐
│ USER runs: python3 device_setup.py                          │
└────────────────────┬─────────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────────┐
│ device_setup.py                                              │
│                                                              │
│  For each device:                                            │
│    1. Light up unique pattern (1,2,3,4 pads)                │
│    2. Ask user: "Which number for this device?"             │
│    3. User inputs: 1, 2, 3, or 4                            │
│    4. Save to config: {serial: number}                      │
│                                                              │
└────────────────────┬─────────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────────┐
│ ~/.maschine_device_config.json created/updated              │
└────────────────────┬─────────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────────┐
│ ALL applications now use this configuration automatically!   │
└──────────────────────────────────────────────────────────────┘
```

### Использование конфигурации

```python
# In any application:
from maschine import setup_devices_with_config

# Devices are automatically sorted by config!
sorted_devices = setup_devices_with_config()

# Extract devices in correct order
devices = [device for device, _ in sorted_devices]

# Now:
# devices[0] = Device 1 (from config)
# devices[1] = Device 2 (from config)
# devices[2] = Device 3 (from config)
# devices[3] = Device 4 (from config)
```

---

## 🎨 Паттерны взаимодействия

### Паттерн 1: Простое приложение (1 устройство)

```python
from maschine import setup_devices_with_config, Color

# Setup (shows device number automatically)
sorted_devices = setup_devices_with_config(max_count=1)

if not sorted_devices:
    print("No devices found!")
    exit(1)

device, device_num = sorted_devices[0]

# Use device
device.set_all_pads(Color.RED)
time.sleep(1)
device.clear()

# Cleanup
device.close()
```

---

### Паттерн 2: Игра для 2 игроков (4 устройства)

```python
from maschine import setup_devices_with_config, Color

# Setup (shows numbers: 1,2,3,4 pads)
sorted_devices = setup_devices_with_config(max_count=4)

if len(sorted_devices) != 4:
    print(f"Need 4 devices, found {len(sorted_devices)}")
    exit(1)

# Extract devices
devices = [device for device, _ in sorted_devices]

# Assign to players
p1_devices = devices[0:2]  # Device 1-2
p2_devices = devices[2:4]  # Device 3-4

# Game loop
while True:
    # Read input from both players simultaneously
    for device in p1_devices:
        pressed = device.read_pads(timeout_ms=1)
        for pad in pressed:
            handle_p1_input(device, pad)

    for device in p2_devices:
        pressed = device.read_pads(timeout_ms=1)
        for pad in pressed:
            handle_p2_input(device, pad)

# Cleanup
for device in devices:
    device.close()
```

---

### Паттерн 3: MIDI Bridge (1-4 устройства, многопоточность)

```python
from maschine import setup_devices_with_config
import threading

# Setup
sorted_devices = setup_devices_with_config()

# Create thread for each device
threads = []
for device, device_num in sorted_devices:
    thread = threading.Thread(
        target=midi_read_loop,
        args=(device, device_num),
        daemon=True
    )
    thread.start()
    threads.append(thread)

# Main thread waits
try:
    while True:
        time.sleep(0.1)
except KeyboardInterrupt:
    pass

# Cleanup
for device, _ in sorted_devices:
    device.close()
```

---

## ⚡ Производительность

### LED Batching (рекомендуется для игр)

**Проблема:** Множество LED операций → множество HID writes → задержка

**Решение:** Batch updates

```python
# ❌ BAD: Multiple HID writes
for pad in [0, 1, 2, 3]:
    device.set_pad_light(pad, Color.RED)  # HID write! (~10ms each)
# Total: 40ms

# ✅ GOOD: Batch with maschine module (auto-optimized)
for pad in [0, 1, 2, 3]:
    device.set_pad_light(pad, Color.RED)  # Updates buffer only
# Internal lock ensures thread-safety, write happens once
# Total: ~10ms (4x faster!)
```

**Модуль `maschine` автоматически оптимизирует это через Lock в `set_pad_light()`!**

---

### Неблокирующий ввод (рекомендуется для игр)

**Для быстрой реакции:**

```python
# Set non-blocking mode (done automatically in connect())
device.device.set_nonblocking(True)

# Read with minimal timeout
while running:
    data = device.device.read(64, timeout_ms=1)  # 1ms!

    if data:
        events = decode_pad_events(data)
        for event in events:
            handle_event(event)

    # Continue loop immediately
    time.sleep(0.001)  # Minimal sleep
```

**Латентность:** <2ms

---

### Многопоточность

**Для MIDI Bridge или многопользовательских игр:**

```python
# Each device in separate thread
for device in devices:
    thread = threading.Thread(
        target=read_loop,
        args=(device,),
        daemon=True
    )
    thread.start()
```

**Преимущества:**
- Параллельное чтение от всех устройств
- Нет блокировок между устройствами
- Низкая латентность

**Важно:** `MaschineDevice` использует `threading.Lock` для thread-safety LED операций!

---

## 📊 Диаграмма компонентов

```
┌─────────────────────────────────────────────────────────────┐
│                         APPLICATIONS                        │
├──────────────┬──────────────┬──────────────┬────────────────┤
│ memory_match │  pvp_whack   │ reaction_game│  midi_bridge   │
└──────┬───────┴──────┬───────┴──────┬───────┴────────┬───────┘
       │              │              │                │
       │              │              │                │
       └──────────────┴──────────────┴────────────────┘
                           │
                           │ imports and uses
                           ▼
       ┌────────────────────────────────────────────┐
       │          maschine module                   │
       │  ┌──────────────────────────────────────┐ │
       │  │ setup_devices_with_config()          │ │  ◄─ Main API
       │  └──────────────────────────────────────┘ │
       │                    │                       │
       │         ┌──────────┴──────────┐           │
       │         │                     │           │
       │  ┌──────▼───────┐     ┌──────▼────────┐  │
       │  │ device.py    │     │ device_config │  │
       │  │              │     │               │  │
       │  │ MaschineDevice│    │ load/save     │  │
       │  │ find_devices │     │ sort          │  │
       │  └──────────────┘     └───────────────┘  │
       │         │                     │           │
       │  ┌──────▼─────────────────────▼────────┐ │
       │  │      constants.py                   │ │
       │  │  Color, PadEventType, etc.          │ │
       │  └─────────────────────────────────────┘ │
       └────────────────────────────────────────────┘
                           │
                           │ uses
                           ▼
       ┌────────────────────────────────────────────┐
       │              hidapi library                │
       │   (Python wrapper for USB HID access)      │
       └────────────────────────────────────────────┘
                           │
                           │ USB HID protocol
                           ▼
       ┌────────────────────────────────────────────┐
       │      Maschine Mikro MK3 Hardware           │
       │   (Up to 4 controllers via USB)            │
       └────────────────────────────────────────────┘
```

---

## 🎯 Ключевые решения архитектуры

### 1. **Единая точка входа**

`setup_devices_with_config()` - всё что нужно приложению:
- Поиск устройств
- Сортировка по конфигурации
- Визуальная идентификация

**Преимущество:** Минимальный boilerplate код в приложениях.

---

### 2. **Centralized Configuration**

Файл `~/.maschine_device_config.json` используется всеми приложениями.

**Преимущество:** Один раз настроил - работает везде.

---

### 3. **Visual Device Identification**

При инициализации каждое устройство показывает свой номер пэдами.

**Преимущество:** Легко проверить правильность подключения.

---

### 4. **Thread-Safe Operations**

`MaschineDevice` использует `threading.Lock` для LED операций.

**Преимущество:** Можно безопасно использовать в многопоточных приложениях.

---

### 5. **Optimized LED Updates**

LED buffer обновляется локально, HID write минимизирован.

**Преимущество:** Высокая производительность в играх.

---

## 📚 Дополнительные документы

- **`PROTOCOL.md`** - Детали HID протокола MK3
- **`DEVICE_SETUP_GUIDE.md`** - Руководство по настройке устройств
- **`MIGRATION_COMPLETE.md`** - Статус миграции приложений
- **`GAMES_PERFORMANCE_REVIEW.md`** - Оптимизация производительности
- **`MIDI_OPTIMIZATION.md`** - Оптимизация MIDI bridge

---

## 🎓 Заключение

Архитектура построена на принципах:
- ✅ Простота использования
- ✅ Нет дублирования кода
- ✅ Единая конфигурация
- ✅ Визуальная наглядность
- ✅ Высокая производительность
- ✅ Расширяемость

**Результат:** Чистый, поддерживаемый и производительный код! 🚀


