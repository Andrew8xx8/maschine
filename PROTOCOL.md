# Maschine Mikro MK3 Protocol Documentation

Complete protocol documentation for the Native Instruments Maschine Mikro MK3 based on reverse engineering and the [r00tman/maschine-mikro-mk3-driver](https://github.com/r00tman/maschine-mikro-mk3-driver) reference.

## Device Identification

- **Vendor ID**: `0x17cc` (Native Instruments)
- **Product ID**: `0x1700` (Maschine Mikro MK3)
- **Interface**: HID (Human Interface Device)

## Initialization Sequence

Before the device sends events, it requires an initialization handshake:

### 1. NHL Registration (Required)
```python
client_id = os.urandom(8)  # Generate unique 8-byte client ID
msg = [0x03, 0x01] + list(client_id) + [0x00] * 54
device.write(msg)
```

### 2. Wake-up Sequences
```python
sequences = [
    [0x01, 0x00, 0x00, 0x02, 0x01, 0x00, 0x00, 0x00] + [0x00] * 56,
    [0x04, 0x00, 0x01, 0x00, 0x00, 0x00] + [0x00] * 58,
    [0x02, 0x00, 0x01] + [0x00] * 61,
    [0x80, 0x00] + [0x00] * 62,
    [0xa0, 0x00, 0x00, 0x00] + [0x00] * 60,
]

for seq in sequences:
    device.write(seq)
    time.sleep(0.05)
```

### 3. Set Non-blocking Mode
```python
device.set_nonblocking(True)
```

## Physical Pad Layout

The pads are numbered 0-15 in the HID protocol, and their physical layout matches the numbering:

```
Physical Layout (top view, controller facing you):
    ┌─────────────────────┐
    │  0   1   2   3  │  <- Top row (farthest from you)
    │  4   5   6   7  │
    │  8   9  10  11  │
    │ 12  13  14  15  │  <- Bottom row (closest to you)
    └─────────────────────┘
```

**Simple sequential layout** - pad indices directly map to physical positions.

## Input Events

### Pad Events (Report ID: 0x02)

**Structure:**
```
Byte 0: 0x02 (Report ID)
Bytes 1-63: Pad data in triplets (index, event_type, velocity)

Each pad event is 3 bytes:
  Byte N: Pad index (0-15)
  Byte N+1: Event type (high nibble) + velocity high bits (low nibble)
  Byte N+2: Velocity low byte
```

**Event Types:**
- `0x00`: PressOn (pad pressed)
- `0x10`: NoteOn (pad hit as note)
- `0x20`: PressOff (pad released)
- `0x30`: NoteOff (note released)
- `0x40`: Aftertouch (continuous pressure)

**Velocity Calculation:**
```python
velocity_12bit = ((buf[i+1] & 0x0f) << 8) | buf[i+2]
velocity_midi = velocity_12bit >> 5  # Scale to MIDI range (0-127)
```

**Example:**
```
[0x02, 0x03, 0x94, 0x12, ...]
       ^     ^     ^
       |     |     velocity low byte (0x12)
       |     event type 0x90 + vel high (0x4)
       pad index 3

Full velocity = (0x4 << 8) | 0x12 = 0x412 = 1042
MIDI velocity = 1042 >> 5 = 32
```

### Button Events (Report ID: 0x01)

**Structure:**
```
Byte 0: 0x01 (Report ID)
Bytes 1-6: Button states (bit field)
Byte 7: Encoder value
Bytes 8-9: Reserved
Byte 10: Slider value
```

**Button Mapping:**
Each byte contains 8 buttons (1 bit per button):
```
Byte 1: Restart, StepLeft, StepRight, Grid, Play, Rec, Erase, Shift
Byte 2: Group, Browse, Sampling, NoteRepeat, Encoder, -, -, -
Byte 3: F1, F2, F3, Control, Nav, NavLeft, NavRight, Main
Byte 4: Scene, Pattern, PadMode, View, Duplicate, Select, Solo, Mute
```

## Output (LED Control)

### LED Buffer Structure

**Size:** 81 bytes total

```
Byte 0: 0x80 (Report ID)
Bytes 1-39: Button LEDs (monochrome, brightness only)
Bytes 40-55: Pad LEDs (16 pads, color palette + brightness)
Bytes 56-80: Slider LEDs (25 segments)
```

### Pad LED Format

**Single byte per pad** (not RGB!):
```
value = (color_index << 2) | (brightness & 0b11)
```

**If brightness is 0x00 (Off):**
```
value = 0
```

### Color Palette

MK3 использует палитру из 17 предопределённых цветов (не прямой RGB).

| Index | Color Name      | Цвет по-русски       | Спектр       |
|-------|-----------------|----------------------|--------------|
| 0     | Off             | Выкл                 | -            |
| 1     | Red             | Красный              | 🔴 Красный   |
| 2     | Orange          | Оранжевый            | 🟠 Оранжевый |
| 3     | Light Orange    | Светло-оранжевый     | 🟠 Оранжевый |
| 4     | Warm Yellow     | Тёплый жёлтый        | 🟡 Жёлтый    |
| 5     | Yellow          | Жёлтый               | 🟡 Жёлтый    |
| 6     | Lime            | Лаймовый             | 🟢 Зелёный   |
| 7     | Green           | Зелёный              | 🟢 Зелёный   |
| 8     | Mint            | Мятный               | 🟢 Зелёный   |
| 9     | Cyan            | Бирюзовый            | 🔵 Голубой   |
| 10    | Turquoise       | Бирюзовый насыщенный | 🔵 Голубой   |
| 11    | Blue            | Синий                | 🔵 Синий     |
| 12    | Plum            | Сливовый             | 🟣 Фиолетовый|
| 13    | Violet          | Фиолетовый           | 🟣 Фиолетовый|
| 14    | Purple          | Пурпурный            | 🟣 Фиолетовый|
| 15    | Magenta         | Маджента             | 🟣 Розовый   |
| 16    | Fuchsia         | Фуксия               | 🟣 Розовый   |
| 17    | White           | Белый                | ⚪ Белый     |

**Порядок радуги:** 1 (Red) → 2-5 (Orange/Yellow) → 6-8 (Green) → 9-11 (Cyan/Blue) → 12-16 (Purple/Magenta) → 17 (White)

### Brightness Levels

| Value | Name | Description |
|-------|------|-------------|
| 0x00 | Off | LED off |
| 0x7c | Dim | Low brightness |
| 0x7e | Normal | Medium brightness |
| 0x7f | Bright | Full brightness |

### Setting Pad Color Example

```python
# Set Pad 0 to Blue with Normal brightness
led_buffer = [0x00] * 81
led_buffer[0] = 0x80  # Report ID

pad_index = 0
color_index = 11  # Blue
brightness = 0x7e  # Normal

value = (color_index << 2) | (brightness & 0b11)
# value = (11 << 2) | (0x7e & 0b11)
# value = 44 | 2 = 46

led_buffer[40 + pad_index] = value
device.write(led_buffer)
```

### Setting Multiple Pads

```python
# Create LED buffer
led_buffer = [0x00] * 81
led_buffer[0] = 0x80

# Set multiple pads
pads = [
    (0, 11, 0x7e),  # Pad 0: Blue, Normal
    (1, 1, 0x7f),   # Pad 1: Red, Bright
    (2, 7, 0x7c),   # Pad 2: Green, Dim
]

for pad_idx, color_idx, brightness in pads:
    if brightness == 0x00:
        value = 0
    else:
        value = (color_idx << 2) | (brightness & 0b11)
    led_buffer[40 + pad_idx] = value

# Write once for all changes
device.write(led_buffer)
```

## Button LED Format

**Single byte per button** (monochrome):

```
Bytes 1-39: Brightness value (0x00-0x7f)
```

Most buttons are white-only. Special cases:
- Group button (bytes 9-11): RGB support (3 bytes)
- Play button: Always green
- Rec button: Always red

## Slider LED Format

**Bytes 56-80** (25 segments):

Each byte is brightness (0x00-0x7f) for the corresponding slider segment.

## Technical Notes

1. **LED Buffer Writes:** Always send the full 81-byte buffer, even if only one LED changed
2. **Timing:** Allow ~50ms between initialization sequences
3. **Non-blocking I/O:** Essential for event loop, use `device.set_nonblocking(True)`
4. **Color Mapping:** RGB values must be mapped to nearest palette color
5. **Brightness Encoding:** Only 2 bits used in pad LED value, mapped to 4 levels

## Reference Implementation

See [maschine_controller.py](maschine_controller.py) for a complete working implementation.

## Credits

Protocol reverse-engineered from:
- [r00tman/maschine-mikro-mk3-driver](https://github.com/r00tman/maschine-mikro-mk3-driver) (Rust)
- Direct HID analysis and testing

