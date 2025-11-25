#!/usr/bin/env python3
"""
Maschine Mikro MK3 Text Show - Multi-Device
============================================

Текстовые сообщения и веселые анимации на 4 контроллерах.
"""

import hid
import time
import os
import sys
import random
import math

VENDOR_ID = 0x17cc
PRODUCT_ID = 0x1700
MAX_DEVICES = 4

# LED configuration
LED_BUFFER_SIZE = 81
PAD_OFFSET = 40

# Colors
COLORS = [
    ('Red', 1), ('Orange', 2), ('Yellow', 5), ('Lime', 6),
    ('Green', 7), ('Mint', 8), ('Cyan', 9), ('Turquoise', 10),
    ('Blue', 11), ('Plum', 12), ('Violet', 13), ('Purple', 14),
    ('Magenta', 15), ('Fuchsia', 16), ('White', 17),
]

BRIGHTNESS_BRIGHT = 0x7f

# Frame durations
TEXT_FRAME_DURATION = 0.15  # Быстрее прокрутка текста
FX_FRAME_DURATION = 0.08    # Скорость эффектов

# 4x4 Font
FONT = {
    'H': [[1,0,1], [1,0,1], [1,1,1], [1,0,1]],
    'A': [[0,1,0], [1,0,1], [1,1,1], [1,0,1]],
    'N': [[1,0,1], [1,1,1], [1,1,1], [1,0,1]],
    'D': [[1,1,0], [1,0,1], [1,0,1], [1,1,0]],
    'S': [[0,1,1], [1,0,0], [0,0,1], [1,1,0]],
    'O': [[1,1,1], [1,0,1], [1,0,1], [1,1,1]],
    'P': [[1,1,1], [1,0,1], [1,1,1], [1,0,0]],
    'E': [[1,1,1], [1,1,0], [1,1,0], [1,1,1]],
    'R': [[1,1,0], [1,0,1], [1,1,0], [1,0,1]],
    'F': [[1,1,1], [1,1,0], [1,1,0], [1,0,0]],
    'M': [[1,0,0,1], [1,1,1,1], [1,0,0,1], [1,0,0,1]],  # 4 wide
    'C': [[0,1,1], [1,0,0], [1,0,0], [0,1,1]],
    ' ': [[0,0,0], [0,0,0], [0,0,0], [0,0,0]],
    '.': [[0,0,0], [0,0,0], [0,0,0], [0,1,0]],
}


class Device:
    """Wrapper for HID device"""
    def __init__(self, device_info):
        self.info = device_info
        self.serial = device_info['serial_number']
        self.device = None
        self.led_buffer = [0x00] * LED_BUFFER_SIZE
        self.led_buffer[0] = 0x80

    def connect(self):
        """Connect and initialize device"""
        try:
            self.device = hid.device()
            self.device.open_path(self.info['path'])

            client_id = os.urandom(8)
            self.device.write([0x03, 0x01] + list(client_id) + [0x00] * 54)
            time.sleep(0.05)

            for seq in [
                [0x01, 0x00, 0x00, 0x02, 0x01, 0x00, 0x00, 0x00] + [0x00] * 56,
                [0x04, 0x00, 0x01, 0x00, 0x00, 0x00] + [0x00] * 58,
                [0x80, 0x00] + [0x00] * 62,
            ]:
                self.device.write(seq)
                time.sleep(0.03)

            self.device.set_nonblocking(True)
            time.sleep(0.1)

            for i in range(16):
                self.led_buffer[PAD_OFFSET + i] = 0
            self.device.write(self.led_buffer)

            return True
        except Exception as e:
            print(f"[{self.serial}] Error: {e}")
            return False

    def set_pattern(self, pattern, color_idx):
        """Set 4x4 pattern on device"""
        for pad_idx in range(16):
            if pattern[pad_idx] == 0:
                value = 0
            else:
                value = (color_idx << 2) | (BRIGHTNESS_BRIGHT & 0b11)
            self.led_buffer[PAD_OFFSET + pad_idx] = value
        try:
            self.device.write(self.led_buffer)
        except:
            pass

    def clear(self):
        """Clear all pads"""
        for i in range(16):
            self.led_buffer[PAD_OFFSET + i] = 0
        try:
            self.device.write(self.led_buffer)
        except:
            pass

    def light_all(self, color_idx):
        """Light all pads"""
        for pad_idx in range(16):
            value = (color_idx << 2) | (BRIGHTNESS_BRIGHT & 0b11)
            self.led_buffer[PAD_OFFSET + pad_idx] = value
        try:
            self.device.write(self.led_buffer)
        except:
            pass

    def close(self):
        """Close device"""
        if self.device:
            self.clear()
            self.device.close()


def find_and_setup_devices():
    """Find, connect and setup 4 devices"""
    device_infos = [d for d in hid.enumerate()
                    if d['vendor_id'] == VENDOR_ID and d['product_id'] == PRODUCT_ID][:4]

    if len(device_infos) != 4:
        print(f"❌ Найдено {len(device_infos)} устройств, требуется 4")
        return None

    devices = []
    for info in device_infos:
        dev = Device(info)
        if dev.connect():
            devices.append(dev)

    if len(devices) != 4:
        return None

    # Quick setup with color identification
    print("\n" + "=" * 70)
    print("НАСТРОЙКА ПОРЯДКА (слева направо)")
    print("=" * 70)

    colors = [('Red', 1), ('Green', 7), ('Blue', 11), ('Yellow', 5)]
    device_positions = {}
    used_positions = set()

    for idx, dev in enumerate(devices):
        color_name, color_idx = colors[idx]
        print(f"\nУстройство светится: {color_name.upper()} [{dev.serial}]")
        dev.light_all(color_idx)
        time.sleep(0.5)

        while True:
            try:
                pos = int(input(f"Позиция (1-4): ").strip())
                if pos < 1 or pos > 4 or pos in used_positions:
                    print("❌ Неверная позиция")
                    continue
                device_positions[dev] = pos
                used_positions.add(pos)
                dev.clear()
                break
            except:
                print("❌ Введите число 1-4")

    return sorted(devices, key=lambda d: device_positions[d])


def text_to_bitmap(text):
    """Convert text to bitmap columns"""
    columns = []
    for char in text.upper():
        if char in FONT:
            char_data = FONT[char]
            width = len(char_data[0])
            for col_idx in range(width):
                col = [char_data[row][col_idx] for row in range(4)]
                columns.append(col)
            columns.append([0, 0, 0, 0])  # Space
    return columns


def bitmap_to_device_patterns(bitmap, offset):
    """Convert bitmap to 4 device patterns"""
    patterns = []
    for device_idx in range(4):
        pattern = [0] * 16
        for col in range(4):
            global_col = offset + (device_idx * 4) + col
            if global_col < len(bitmap):
                column = bitmap[global_col]
                for row in range(4):
                    pad_idx = row * 4 + col
                    pattern[pad_idx] = column[row]
        patterns.append(pattern)
    return patterns


def scroll_text(devices, text, color_idx, loops=3):
    """Scroll text across display for N complete loops"""
    bitmap = text_to_bitmap(text)
    offset = 0
    current_loop = 0

    while current_loop < loops:
        patterns = bitmap_to_device_patterns(bitmap, offset)
        for dev_idx, dev in enumerate(devices):
            dev.set_pattern(patterns[dev_idx], color_idx)

        time.sleep(TEXT_FRAME_DURATION)
        offset += 1
        if offset >= len(bitmap):
            offset = 0
            current_loop += 1


def fx_wave(devices, duration=8):
    """Волна снизу вверх"""
    start_time = time.time()
    frame = 0
    color_idx = random.choice(COLORS)[1]

    while time.time() - start_time < duration:
        for dev_idx, dev in enumerate(devices):
            pattern = [0] * 16
            # Синусоидальная волна
            for col in range(4):
                x = (dev_idx * 4 + col) / 16.0 * 2 * math.pi
                wave_height = int((math.sin(x + frame * 0.3) + 1) * 2)  # 0-3

                for row in range(4):
                    if row == wave_height:
                        pad_idx = row * 4 + col
                        pattern[pad_idx] = 1

            dev.set_pattern(pattern, color_idx)

        frame += 1
        time.sleep(FX_FRAME_DURATION)


def fx_spiral(devices, duration=8):
    """Спираль от центра"""
    start_time = time.time()
    frame = 0
    color_idx = random.choice(COLORS)[1]

    # Координаты всех 64 пэдов (16x4)
    positions = []
    for dev_idx in range(4):
        for pad_idx in range(16):
            row = pad_idx // 4
            col = pad_idx % 4
            global_col = dev_idx * 4 + col
            positions.append((dev_idx, pad_idx, global_col, row))

    # Сортируем по расстоянию от центра
    center_x, center_y = 7.5, 1.5
    positions.sort(key=lambda p: math.sqrt((p[2] - center_x)**2 + (p[3] - center_y)**2))

    while time.time() - start_time < duration:
        active_count = int((frame % 80) * 0.8)

        patterns = [[0]*16 for _ in range(4)]

        for i in range(min(active_count, len(positions))):
            dev_idx, pad_idx, _, _ = positions[i]
            patterns[dev_idx][pad_idx] = 1

        for dev_idx, dev in enumerate(devices):
            dev.set_pattern(patterns[dev_idx], color_idx)

        frame += 1
        time.sleep(FX_FRAME_DURATION)


def fx_rain(devices, duration=8):
    """Дождь"""
    start_time = time.time()
    color_idx = random.choice(COLORS)[1]

    # Капли для каждой колонки (16 колонок)
    drops = [[random.randint(-10, 3) for _ in range(16)] for _ in range(2)]  # 2 слоя

    while time.time() - start_time < duration:
        patterns = [[0]*16 for _ in range(4)]

        for layer in drops:
            for col_global in range(16):
                row = layer[col_global]
                if 0 <= row < 4:
                    dev_idx = col_global // 4
                    col_local = col_global % 4
                    pad_idx = row * 4 + col_local
                    patterns[dev_idx][pad_idx] = 1

                # Двигаем каплю вниз
                layer[col_global] += 1
                if layer[col_global] > 5:
                    layer[col_global] = random.randint(-5, -1)

        for dev_idx, dev in enumerate(devices):
            dev.set_pattern(patterns[dev_idx], color_idx)

        time.sleep(FX_FRAME_DURATION * 2)


def fx_flash(devices, duration=8):
    """Быстрые вспышки разными цветами"""
    start_time = time.time()

    while time.time() - start_time < duration:
        color_idx = random.choice(COLORS)[1]
        pattern = [1] * 16

        for dev in devices:
            dev.set_pattern(pattern, color_idx)

        time.sleep(0.1)

        for dev in devices:
            dev.clear()

        time.sleep(0.05)


def main():
    print("=" * 70)
    print("🎬 Maschine Mikro MK3 Text Show")
    print("=" * 70)
    print()

    devices = find_and_setup_devices()
    if not devices:
        print("\n❌ Не удалось подключить устройства")
        return

    print("\n✅ Все устройства готовы!")
    print()
    print("=" * 70)
    print("ПРОГРАММА: Бесконечный цикл")
    print("=" * 70)
    print("  HANDS ON → Эффект → HANDS ON → Эффект → ...")
    print()
    print("  Доступные эффекты:")
    print("    🌊 Волна")
    print("    🌀 Спираль")
    print("    🌧️  Дождь")
    print("    ⚡ Вспышки")
    print()
    print("  Нажмите Ctrl+C для остановки")
    print("=" * 70)
    print()
    input("Нажмите Enter для старта...")
    print()

    # Effects list
    effects = [
        ("🌊 Волна", fx_wave),
        ("🌀 Спираль", fx_spiral),
        ("🌧️  Дождь", fx_rain),
        ("⚡ Вспышки", fx_flash),
    ]

    try:
        cycle_count = 0

        while True:
            cycle_count += 1
            print(f"\n{'='*70}")
            print(f"ЦИКЛ {cycle_count}")
            print('='*70)

            # Show HANDS ON
            print("🎬 HANDS ON")
            scroll_text(devices, "  HANDS ON  ", 9, loops=2)  # Cyan, 2 прокрутки

            # Pick random effect
            effect_name, effect_func = random.choice(effects)
            print(f"✨ {effect_name}")
            effect_func(devices)

            # Small pause between cycles
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\n\n🛑 Шоу остановлено")

    except KeyboardInterrupt:
        print("\n\n🛑 Прервано")

    finally:
        print("\nОчистка...")
        for dev in devices:
            dev.close()
        print("✓ Готово\n")


if __name__ == "__main__":
    main()

