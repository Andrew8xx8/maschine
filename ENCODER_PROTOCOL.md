# 🎚️ Maschine Mikro MK3 - Encoder Protocol

Полная документация протокола энкодера на основе реверс-инжиниринга HID событий.

---

## 📊 HID Report Structure (0x01)

```
Byte 0:  0x01 (Report ID)
Bytes 1-4: Button states (битовые маски)
Byte 5:  Encoder Press (0x00 = released, 0x80 = pressed)
Byte 6:  Encoder Touch (0x00 = not touched, 0x01 = touched)
Byte 7:  Encoder Position (0x00-0x0F, циклически)
Bytes 8-9: Constants (0x83, 0xd4)
```

---

## 🎚️ Encoder Events

### 1. Encoder Touch (Прикосновение)

**HID данные:**
```
📥 [ 0]=0x01 [ 6]=0x01 [ 7]=0x03 [ 8]=0x83 [ 9]=0xd4
             ^^^^^^^
             Touch detected
```

**Индикатор:** `data[6] == 0x01`

**Использование:**
- Определить что пользователь касается энкодера
- Начать отслеживание вращения
- Включить визуальную обратную связь

---

### 2. Encoder Press (Клик)

**HID данные:**
```
📥 [ 0]=0x01 [ 5]=0x80 [ 6]=0x01 [ 7]=0x03 [ 8]=0x83 [ 9]=0xd4
             ^^^^^^^
             Press detected
```

**Индикатор:** `data[5] == 0x80`

**Использование:**
- Кнопка энкодера нажата
- Обычно используется как Enter/OK
- Часто комбинируется с другими кнопками

---

### 3. Encoder Rotation (Вращение)

**HID данные (вращение вправо):**
```
[ 7]=0x03  → start
[ 7]=0x04  → +1
[ 7]=0x05  → +1
[ 7]=0x06  → +1
...
[ 7]=0x0e  → +1
[ 7]=0x0f  → +1
[ 7]=0x00  → wrap around (переход через 0)
[ 7]=0x01  → +1
[ 7]=0x02  → +1
[ 7]=0x03  → back to start
```

**Характеристики:**
- Абсолютная позиция (не дельта!)
- Диапазон: 0x00 - 0x0F (16 позиций)
- Циклическое вращение (wrap around)
- Только при касании (`data[6] == 0x01`)

---

## 💻 Реализация

### Python - Простое отслеживание

```python
last_position = None

while True:
    data = device.read(64, timeout_ms=10)

    if data and data[0] == 0x01:
        encoder_touch = data[6]
        encoder_position = data[7]

        if encoder_touch == 0x01:
            if last_position is not None:
                delta = encoder_position - last_position

                # Handle wrap around
                if delta > 8:
                    delta -= 16  # CCW через 0
                elif delta < -8:
                    delta += 16  # CW через 0

                if delta > 0:
                    print(f"↻ CW: {delta} steps")
                elif delta < 0:
                    print(f"↺ CCW: {abs(delta)} steps")

            last_position = encoder_position
        else:
            last_position = None
```

---

### Python - Полная обработка

```python
class EncoderState:
    def __init__(self):
        self.last_position = None
        self.is_touched = False
        self.is_pressed = False

    def update(self, data):
        if not data or data[0] != 0x01:
            return None

        encoder_press = data[5] == 0x80
        encoder_touch = data[6] == 0x01
        encoder_position = data[7]

        event = None

        # Press event
        if encoder_press and not self.is_pressed:
            event = {'type': 'press', 'position': encoder_position}
            self.is_pressed = True
        elif not encoder_press and self.is_pressed:
            event = {'type': 'release', 'position': encoder_position}
            self.is_pressed = False

        # Touch event
        if encoder_touch and not self.is_touched:
            event = {'type': 'touch', 'position': encoder_position}
            self.is_touched = True
            self.last_position = encoder_position
        elif not encoder_touch and self.is_touched:
            event = {'type': 'untouch'}
            self.is_touched = False
            self.last_position = None

        # Rotation event
        if encoder_touch and self.last_position is not None:
            if encoder_position != self.last_position:
                delta = encoder_position - self.last_position

                # Handle wrap around
                if delta > 8:
                    delta -= 16
                elif delta < -8:
                    delta += 16

                if delta != 0:
                    event = {
                        'type': 'rotate',
                        'delta': delta,
                        'position': encoder_position,
                        'direction': 'cw' if delta > 0 else 'ccw'
                    }

                self.last_position = encoder_position

        return event

# Usage
encoder = EncoderState()

while True:
    data = device.read(64, timeout_ms=10)
    event = encoder.update(data)

    if event:
        if event['type'] == 'rotate':
            print(f"Rotated {event['direction'].upper()}: {event['delta']}")
        elif event['type'] == 'press':
            print("Encoder pressed")
        elif event['type'] == 'touch':
            print("Encoder touched")
```

---

## 🎮 Примеры использования

### 1. Volume Control

```python
volume = 50  # 0-100

def on_encoder_event(event):
    global volume

    if event['type'] == 'rotate':
        volume += event['delta'] * 5  # 5% per step
        volume = max(0, min(100, volume))
        print(f"Volume: {volume}%")

        # Visual feedback on pads
        lit_pads = int(volume / 100 * 16)
        for i in range(16):
            if i < lit_pads:
                device.set_pad_light(i, Color.GREEN, on=True)
            else:
                device.set_pad_light(i, Color.OFF, on=False)
```

---

### 2. Menu Navigation

```python
menu_items = ['Play', 'Record', 'Stop', 'Settings']
selected = 0

def on_encoder_event(event):
    global selected

    if event['type'] == 'rotate':
        selected += event['delta']
        selected = selected % len(menu_items)
        print(f"Selected: {menu_items[selected]}")

    elif event['type'] == 'press':
        print(f"Activated: {menu_items[selected]}")
```

---

### 3. Parameter Tweaking (Fine Control)

```python
param_value = 0.5  # 0.0 - 1.0

def on_encoder_event(event):
    global param_value

    if event['type'] == 'rotate':
        # Fine control: 0.01 per step
        param_value += event['delta'] * 0.01
        param_value = max(0.0, min(1.0, param_value))

        print(f"Parameter: {param_value:.2f}")
```

---

## 🔍 Debugging

Используйте `debug_controller.py` для отладки:

```bash
python3 debug_controller.py
# Выберите: 5 - Дебаг энкодера

# Или напрямую:
python3 debug_controller.py --buttons
```

**Вывод:**
```
👆 Encoder TOUCH
🎚️  Encoder: ↻ CW pos= 4 delta=+1
🎚️  Encoder: ↻ CW pos= 5 delta=+1
🎚️  Encoder: ↻ CW pos= 6 delta=+1
🔘 Encoder PRESS
🎚️  Encoder: ↺ CCW pos= 5 delta=-1
🎚️  Encoder: ↺ CCW pos= 4 delta=-1
🖐️  Encoder RELEASE
```

---

## ⚠️ Important Notes

### 1. Абсолютная позиция, не дельта

Энкодер отправляет **абсолютную позицию** (0-15), а не относительную дельту.
Вы должны сами вычислять разницу между текущей и предыдущей позицией.

### 2. Циклическое вращение

Позиция циклична:
- `0x0F → 0x00` (вращение вправо через 0)
- `0x00 → 0x0F` (вращение влево через 0)

Обязательно обрабатывайте wrap-around!

### 3. Только при касании

Позиция обновляется **только при касании** энкодера (`data[6] == 0x01`).
Когда не касаетесь - данные не обновляются.

### 4. Разрешение

16 позиций на полный оборот = довольно грубое разрешение.
Для точного контроля используйте мультипликатор на delta.

---

## 📊 Wrap-around Logic

```python
def calculate_delta(new_pos, old_pos):
    """
    Правильный расчет дельты с учетом wrap-around

    Позиции: 0-15 циклически
    """
    delta = new_pos - old_pos

    # Если дельта больше половины диапазона - это wrap
    if delta > 8:
        # Вращение CCW через 0: 15 → 0 = -1, not +1
        delta -= 16
    elif delta < -8:
        # Вращение CW через 0: 0 → 15 = +1, not -1
        delta += 16

    return delta

# Примеры:
calculate_delta(1, 0)   # +1 (CW)
calculate_delta(0, 1)   # -1 (CCW)
calculate_delta(0, 15)  # +1 (CW через 0, not -15!)
calculate_delta(15, 0)  # -1 (CCW через 0, not +15!)
calculate_delta(8, 0)   # +8 (CW half rotation)
calculate_delta(0, 8)   # -8 (CCW half rotation)
```

---

## ✅ Testing Checklist

- [ ] Encoder touch detection
- [ ] Encoder press detection
- [ ] Clockwise rotation
- [ ] Counter-clockwise rotation
- [ ] Wrap around 0x0F → 0x00
- [ ] Wrap around 0x00 → 0x0F
- [ ] Fast rotation (multiple steps)
- [ ] Combined press + rotate
- [ ] Touch release detection

---

**Последнее обновление:** 2025-11-21
**Проверено на:** Maschine Mikro MK3 firmware v1.x

