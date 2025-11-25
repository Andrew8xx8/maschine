# 🖥️ Maschine Mikro MK3 - Screen Protocol

Полная документация протокола управления экранами контроллера.

---

## 📊 Характеристики экрана

### Физическое расположение
- **Один монохромный LCD экран**
- Расположен над падами, под энкодером

### Технические характеристики
- **Разрешение:** 128 x 32 пикселей
- **Тип:** Монохромный (черно-белый)
- **Битовая карта:** 512 байт (128 * 32 / 8)
- **Логика:** Инвертированная (0 = пиксель включен, 1 = выключен)

---

## 📤 HID Protocol

### Структура передачи

Данные экрана передаются двумя HID-пакетами:

```
Пакет 1 (верхняя половина):
[HEADER_HI] + [256 байт данных]

Пакет 2 (нижняя половина):
[HEADER_LO] + [256 байт данных]
```

### Headers

```python
HEADER_HI = [0xe0, 0x00, 0x00, 0x00, 0x00, 0x80, 0x00, 0x02, 0x00]
HEADER_LO = [0xe0, 0x00, 0x00, 0x02, 0x00, 0x80, 0x00, 0x02, 0x00]
#                           ^^
#                           Отличие: 0x00 vs 0x02
```

---

## 🗺️ Bitmap Layout

### Организация памяти

Экран организован по-байтно с вертикальной ориентацией битов:

```
128 пикселей (ширина)
├─────────────────────────────────────┐
│ Byte 0                  Byte 127    │ ← Строки 0-7   (chunk 0)
│ Byte 128                Byte 255    │ ← Строки 8-15  (chunk 1)
│ Byte 256                Byte 383    │ ← Строки 16-23 (chunk 2)
│ Byte 384                Byte 511    │ ← Строки 24-31 (chunk 3)
└─────────────────────────────────────┘
32 пикселя (высота)
```

### Битовая структура каждого байта

Каждый байт кодирует **8 вертикальных пикселей**:

```
Byte в позиции (x, chunk):
  bit 0 → пиксель (x, chunk*8 + 0)
  bit 1 → пиксель (x, chunk*8 + 1)
  bit 2 → пиксель (x, chunk*8 + 2)
  bit 3 → пиксель (x, chunk*8 + 3)
  bit 4 → пиксель (x, chunk*8 + 4)
  bit 5 → пиксель (x, chunk*8 + 5)
  bit 6 → пиксель (x, chunk*8 + 6)
  bit 7 → пиксель (x, chunk*8 + 7)
```

### Индексация

```python
def get_byte_index(x, y):
    """Получить индекс байта для пикселя (x, y)"""
    chunk = y // 8
    return chunk * 128 + x

def get_bit_mask(y):
    """Получить битовую маску для пикселя на Y"""
    y_mod = y % 8
    return 1 << y_mod
```

---

## 💻 Примеры кода

### 1. Очистка экрана

```python
from maschine import Screen

screen = Screen()
screen.clear()  # Все пиксели выключены (0xff)
screen.write(device.device)
```

### 2. Установка пикселя

```python
screen = Screen()

# Включить пиксель (10, 20)
screen.set_pixel(10, 20, on=True)

# Выключить пиксель (30, 40)
screen.set_pixel(30, 40, on=False)

# Отправить на устройство
screen.write(device.device)
```

### 3. Рисование линии

```python
screen = Screen()

# Диагональ
screen.draw_line(0, 0, 127, 31, on=True)

# Горизонтальная линия
screen.draw_line(0, 16, 127, 16, on=True)

screen.write(device.device)
```

### 4. Рисование прямоугольника

```python
screen = Screen()

# Контур
screen.draw_rect(10, 10, 50, 30, filled=False, on=True)

# Заполненный
screen.draw_rect(70, 10, 50, 30, filled=True, on=True)

screen.write(device.device)
```

### 5. Рисование окружности

```python
screen = Screen()

# Контур окружности
screen.draw_circle(64, 16, 15, filled=False, on=True)

# Заполненный круг
screen.draw_circle(64, 16, 8, filled=True, on=True)

screen.write(device.device)
```

### 6. Вывод текста

```python
from maschine import Screen
from maschine.screen_font import draw_text_5x7, draw_time

screen = Screen()

# Текст
draw_text_5x7(screen, 10, 10, "HELLO", scale=2)

# Время
draw_time(screen, 10, 30, hours=12, minutes=34, seconds=56, scale=1)

screen.write(device.device)
```

---

## 🎨 Полный пример: Часы

```python
#!/usr/bin/env python3
import time
from datetime import datetime
from maschine import find_devices, Screen
from maschine.screen_font import draw_time, draw_text_5x7

# Найти устройство
devices = find_devices(max_count=1)
if not devices:
    print("Device not found!")
    exit(1)

device = devices[0]
screen = Screen()

try:
    while True:
        screen.clear()

        now = datetime.now()

        # Рамка
        screen.draw_rect(0, 0, 128, 32, filled=False, on=True)

        # Заголовок
        draw_text_5x7(screen, 25, 5, "MASCHINE", scale=1)

        # Время
        draw_time(screen, 10, 20, now.hour, now.minute, now.second, scale=2)

        # Дата
        date_str = now.strftime("%d-%m-%Y")
        draw_text_5x7(screen, 25, 50, date_str, scale=1)

        # Обновить экран
        screen.write(device.device)

        time.sleep(0.5)

except KeyboardInterrupt:
    screen.clear()
    screen.write(device.device)
    print("\nBye!")
```

---

## 🎬 Демо программа

Запустите интерактивное демо:

```bash
python3 screen_demo.py
```

**Доступные демо:**
1. **Графические паттерны** - рамки, линии, круги, шахматная доска
2. **Текст и шрифты** - цифры, буквы, разные масштабы
3. **Часы** - работающие часы в реальном времени
4. **Анимации** - движущиеся объекты, вращение

---

## 📐 Coordinate System

```
(0,0)                           (127,0)
  ┌───────────────────────────────┐
  │                               │
  │         SCREEN                │
  │         (64,16)               │
  │            •                  │
  │                               │
  └───────────────────────────────┘
(0,31)                          (127,31)
```

- **X:** 0 (слева) → 127 (справа)
- **Y:** 0 (сверху) → 31 (снизу)

---

## 🔧 Low-Level Details

### Инвертированная логика

```python
# 0 = пиксель ВКЛЮЧЕН (черный)
# 1 = пиксель ВЫКЛЮЧЕН (белый фон)

# Включить пиксель
buffer[idx] &= ~mask  # Clear bit

# Выключить пиксель
buffer[idx] |= mask   # Set bit
```

### Почему инвертированная?

Это особенность LCD контроллера - при сбросе (0xff) экран должен быть белым.

### Передача данных

```python
# Отправка на устройство
msg_hi = HEADER_HI + buffer[:256]    # Верхняя половина
msg_lo = HEADER_LO + buffer[256:]    # Нижняя половина

device.write(msg_hi)
device.write(msg_lo)
```

---

## 🎯 Best Practices

### 1. Batch Updates

```python
# ✅ GOOD - одна отправка
screen.clear()
screen.draw_line(0, 0, 127, 63)
screen.draw_circle(64, 32, 20)
screen.write(device.device)

# ❌ BAD - много отправок
screen.clear()
screen.write(device.device)
screen.draw_line(0, 0, 127, 63)
screen.write(device.device)
screen.draw_circle(64, 32, 20)
screen.write(device.device)
```

### 2. Bounds Checking

```python
# Screen класс автоматически проверяет границы
screen.set_pixel(-10, 200, on=True)  # Игнорируется
screen.set_pixel(128, 64, on=True)   # Игнорируется
```

### 3. Clear Before Draw

```python
# Всегда начинайте с чистого экрана
screen.clear()
# ... рисуйте ...
screen.write(device.device)
```

### 4. Minimize Writes

```python
# Обновляйте экран не чаще 10-20 раз в секунду
import time

while True:
    screen.clear()
    # ... рисуйте ...
    screen.write(device.device)
    time.sleep(0.05)  # 20 FPS
```

---

## 🔍 Debugging

### Визуализация буфера в консоли

```python
def print_buffer_ascii(screen):
    """Вывести экран в консоль ASCII-артом"""
    for y in range(32):
        line = ""
        for x in range(128):
            if screen.get_pixel(x, y):
                line += "█"
            else:
                line += " "
        print(line)

# Использование
screen = Screen()
screen.draw_circle(64, 32, 20)
print_buffer_ascii(screen)
```

### Проверка байта

```python
def debug_byte(screen, x, y):
    """Показать байт, содержащий пиксель"""
    chunk = y // 8
    idx = chunk * 128 + x
    byte = screen.buffer[idx]
    print(f"Pixel ({x},{y}) -> byte[{idx}] = 0x{byte:02x} = 0b{byte:08b}")
```

---

## 📚 API Reference

### Screen Class

```python
class Screen:
    def __init__(self)
    def clear(self)
    def fill(self)
    def get_pixel(self, x: int, y: int) -> bool
    def set_pixel(self, x: int, y: int, on: bool = True)
    def draw_line(self, x0: int, y0: int, x1: int, y1: int, on: bool = True)
    def draw_rect(self, x: int, y: int, w: int, h: int, filled: bool = False, on: bool = True)
    def draw_circle(self, xc: int, yc: int, r: int, filled: bool = False, on: bool = True)
    def write(self, device) -> bool
```

### Font Functions

```python
from maschine.screen_font import (
    draw_digit,      # Цифры 0-9 (8x8)
    draw_text_5x7,   # Буквы и цифры (5x7)
    draw_time,       # Время HH:MM:SS
)

draw_digit(screen, x, y, digit, scale=1)
draw_text_5x7(screen, x, y, text, scale=1)
draw_time(screen, x, y, hours, minutes, seconds, scale=2)
```

---

## ⚠️ Known Issues

### 1. Скорость обновления

Не рекомендуется обновлять экран чаще 20-30 раз в секунду.

### 2. Один экран

У Mikro MK3 только один экран 128x64, в отличие от полноразмерной Maschine, у которой два.

### 3. Шрифты

Встроенные шрифты - только заглавные буквы латиницы и цифры.
Для кириллицы или других символов нужно добавить свой шрифт.

---

## 🚀 TODO

- [ ] Дополнительные шрифты (кириллица, иконки)
- [ ] Спрайты и битмапы
- [ ] Сглаживание (anti-aliasing)
- [ ] Эффекты переходов
- [ ] Библиотека виджетов (кнопки, меню, прогресс-бары)

---

**Последнее обновление:** 2025-11-21
**Основано на:** `maschine-mikro-mk3-driver/crates/maschine_library/src/screen.rs`

