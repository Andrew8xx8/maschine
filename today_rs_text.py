#!/usr/bin/env python3
"""
Maschine Mikro MK3 Multi-Device Text Display
=============================================

Использует 4 контроллера как единый дисплей 16x4 для прокручивающегося текста.

Layout:
[Device 1: 4x4] [Device 2: 4x4] [Device 3: 4x4] [Device 4: 4x4]
= 16 columns x 4 rows
"""

import hid
import time
import os
import sys
import random

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

# Frame duration
FRAME_DURATION = 0.3

# 4x4 Font
FONT = {
    'T': [[1,1,1], [0,1,0], [0,1,0], [0,1,0]],
    'O': [[1,1,1], [1,0,1], [1,0,1], [1,1,1]],
    'D': [[1,1,0], [1,0,1], [1,0,1], [1,1,0]],
    'A': [[0,1,0], [1,0,1], [1,1,1], [1,0,1]],
    'Y': [[1,0,1], [1,0,1], [0,1,0], [0,1,0]],
    'R': [[1,1,0], [1,0,1], [1,1,0], [1,0,1]],
    'S': [[0,1,1], [1,0,0], [0,0,1], [1,1,0]],
    ' ': [[0,0,0], [0,0,0], [0,0,0], [0,0,0]],
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

            # Initialize
            client_id = os.urandom(8)
            self.device.write([0x03, 0x01] + list(client_id) + [0x00] * 54)
            time.sleep(0.05)

            sequences = [
                [0x01, 0x00, 0x00, 0x02, 0x01, 0x00, 0x00, 0x00] + [0x00] * 56,
                [0x04, 0x00, 0x01, 0x00, 0x00, 0x00] + [0x00] * 58,
                [0x80, 0x00] + [0x00] * 62,
            ]

            for seq in sequences:
                self.device.write(seq)
                time.sleep(0.03)

            self.device.set_nonblocking(True)
            time.sleep(0.1)

            # Clear all pads
            for i in range(16):
                self.led_buffer[PAD_OFFSET + i] = 0
            self.device.write(self.led_buffer)

            return True

        except Exception as e:
            print(f"[{self.serial}] Error connecting: {e}")
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
        except Exception as e:
            print(f"[{self.serial}] Write error: {e}")

    def clear(self):
        """Clear all pads"""
        for i in range(16):
            self.led_buffer[PAD_OFFSET + i] = 0
        try:
            self.device.write(self.led_buffer)
        except:
            pass

    def light_all(self, color_idx):
        """Light all pads with color"""
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


def find_devices():
    """Find all connected Maschine devices"""
    all_devices = hid.enumerate()
    maschine_devices = [d for d in all_devices
                        if d['vendor_id'] == VENDOR_ID
                        and d['product_id'] == PRODUCT_ID]
    return maschine_devices[:MAX_DEVICES]


def setup_device_order(devices):
    """Interactive setup to define device order (left to right)"""
    print("\n" + "=" * 70)
    print("НАСТРОЙКА ПОРЯДКА УСТРОЙСТВ")
    print("=" * 70)
    print()
    print("4 контроллера будут работать как единый дисплей 16x4:")
    print()
    print("  [Позиция 1] [Позиция 2] [Позиция 3] [Позиция 4]")
    print("     4x4         4x4         4x4         4x4")
    print("   (левый)                             (правый)")
    print()
    print("Я буду подсвечивать каждое устройство разными цветами.")
    print("Вы определяете его позицию слева направо (1, 2, 3, 4).")
    print()

    skip = input("Пропустить настройку и использовать автоматический порядок? (y/n): ").strip().lower()
    if skip in ['y', 'yes', 'д', 'да']:
        print("\n✓ Используется автоматический порядок\n")
        return devices

    print()

    # Colors for identification
    identifier_colors = [
        ('Red', 1), ('Green', 7), ('Blue', 11), ('Yellow', 5),
    ]

    device_positions = {}
    used_positions = set()

    for idx, dev in enumerate(devices):
        print("=" * 70)
        color_name, color_idx = identifier_colors[idx]

        print(f"\nПодсвечиваю устройство...")
        print(f"Serial: {dev.serial}")
        print(f"Цвет: {color_name.upper()}")
        print()

        # Light up this device
        dev.light_all(color_idx)
        time.sleep(0.8)

        while True:
            try:
                available = [i for i in range(1, 5) if i not in used_positions]
                print(f"Доступные позиции: {', '.join(map(str, available))}")
                position = input(f"Введите позицию (1=левое, 4=правое): ").strip()

                position = int(position)

                if position < 1 or position > 4:
                    print(f"❌ Позиция должна быть от 1 до 4")
                    continue

                if position in used_positions:
                    print(f"❌ Позиция {position} уже занята")
                    continue

                device_positions[dev] = position
                used_positions.add(position)

                print(f"✓ Устройство {dev.serial} -> Позиция {position}")

                time.sleep(0.3)
                dev.clear()
                time.sleep(0.2)

                break

            except ValueError:
                print("❌ Введите число")
            except KeyboardInterrupt:
                print("\n\n❌ Прервано пользователем")
                for d in devices:
                    d.close()
                sys.exit(0)

        print()

    # Sort devices by position
    sorted_devices = sorted(devices, key=lambda d: device_positions[d])

    print("=" * 70)
    print("ПОРЯДОК УСТРОЙСТВ (слева направо):")
    print("=" * 70)
    for i, dev in enumerate(sorted_devices, 1):
        print(f"  Позиция {i}: {dev.serial}")
    print()

    # Visual confirmation - blink each device in order
    print("Визуальное подтверждение (устройства мигнут по очереди)...")
    time.sleep(1)

    for i, dev in enumerate(sorted_devices, 1):
        print(f"  Позиция {i} мигает...", flush=True)
        # Blink pattern: show position number
        for _ in range(2):
            dev.light_all(17)  # White
            time.sleep(0.3)
            dev.clear()
            time.sleep(0.2)

    print()
    confirm = input("Порядок правильный? (y/n): ").strip().lower()
    if confirm not in ['y', 'yes', 'д', 'да']:
        print("\n⚠️  Перезапустите программу для настройки заново\n")
        for d in devices:
            d.close()
        sys.exit(0)

    print("✅ Порядок подтверждён!\n")
    return sorted_devices


def text_to_bitmap(text):
    """Convert text to bitmap columns"""
    columns = []

    for char in text.upper():
        if char in FONT:
            char_cols = FONT[char]
            # Add character columns
            for col_idx in range(len(char_cols[0])):
                col = [char_cols[row][col_idx] for row in range(4)]
                columns.append(col)
            # Add space between letters
            columns.append([0, 0, 0, 0])

    return columns


def bitmap_to_device_patterns(bitmap, offset, num_devices):
    """
    Convert bitmap to patterns for each device

    Args:
        bitmap: List of columns
        offset: Starting column offset
        num_devices: Number of devices (1-4)

    Returns:
        List of 16-element patterns (one per device)
    """
    patterns = []

    for device_idx in range(num_devices):
        pattern = [0] * 16

        # Each device shows 4 columns
        for col in range(4):
            global_col = offset + (device_idx * 4) + col

            if global_col < len(bitmap):
                column = bitmap[global_col]

                # Map to pads
                for row in range(4):
                    pad_idx = row * 4 + col
                    pattern[pad_idx] = column[row]

        patterns.append(pattern)

    return patterns


def print_full_display(devices, patterns):
    """Print visual representation of full display"""
    for row in range(4):
        for dev_idx in range(len(devices)):
            for col in range(4):
                pad_idx = row * 4 + col
                print("█" if patterns[dev_idx][pad_idx] else "·", end="")
            print(" ", end="")  # Space between devices
        print()


def main():
    print("=" * 70)
    print("📺 Maschine Mikro MK3 Multi-Device Text Display")
    print("=" * 70)
    print()
    print("⚠️  Требуется РОВНО 4 контроллера для работы дисплея 16x4!")
    print()

    # Find devices
    print("🔍 Searching for devices...")
    device_infos = find_devices()

    if not device_infos:
        print("❌ No devices found")
        print("\nTroubleshooting:")
        print("  1. Connect your Maschine Mikro MK3 devices")
        print("  2. Kill NIHardwareAgent: killall NIHardwareAgent")
        return

    print(f"✓ Found {len(device_infos)} device(s)")

    # Check if we have exactly 4 devices
    if len(device_infos) != 4:
        print()
        print(f"❌ Ошибка: найдено {len(device_infos)} устройств, требуется ровно 4")
        print()
        print("Для работы дисплея 16x4 необходимо подключить все 4 контроллера.")
        return

    print()

    # Connect devices
    devices = []
    for info in device_infos:
        dev = Device(info)
        if dev.connect():
            devices.append(dev)
            print(f"  [{dev.serial}] Connected")

    if len(devices) != 4:
        print(f"\n❌ Удалось подключить только {len(devices)}/4 устройств")
        for dev in devices:
            dev.close()
        return

    print(f"\n✅ Успешно подключены все 4 устройства!")

    print("\nПодготовка устройств...")
    time.sleep(1)

    # Setup device order (left to right)
    devices = setup_device_order(devices)

    # Display info
    print("=" * 70)
    print("Конфигурация дисплея:")
    print("=" * 70)
    print(f"  Размер: 16x4 пикселей (4 устройства по 4x4)")
    print(f"  Устройства: {len(devices)}")
    print()
    print("  Layout:")
    print("    [Dev 1] [Dev 2] [Dev 3] [Dev 4]")
    for i, dev in enumerate(devices, 1):
        print(f"    {i}: {dev.serial}")
    print()

    # Convert text to bitmap
    text = "  TODAY.RS  "
    print(f"Text: '{text}'")

    bitmap = text_to_bitmap(text)
    print(f"Text width: {len(bitmap)} columns")
    print()

    # Choose color
    color_name, color_idx = random.choice(COLORS)
    print(f"Color: {color_name}")
    print()

    print("Starting scroll animation...")
    print("Press Ctrl+C to stop\n")

    time.sleep(1)

    # Scroll animation
    offset = 0
    frame_count = 0

    try:
        while True:
            # Get patterns for all devices
            patterns = bitmap_to_device_patterns(bitmap, offset, len(devices))

            # Display on all devices
            for dev_idx, dev in enumerate(devices):
                dev.set_pattern(patterns[dev_idx], color_idx)

            # Debug output
            if frame_count % 10 == 0:
                print(f"Frame {frame_count}, Offset {offset}:")
                print_full_display(devices, patterns)
                print()

            time.sleep(FRAME_DURATION)

            # Move to next column
            offset += 1

            # Loop back
            if offset >= len(bitmap):
                offset = 0
                # Change color on loop
                color_name, color_idx = random.choice(COLORS)
                print(f"🎨 New color: {color_name}")

            frame_count += 1

    except KeyboardInterrupt:
        print("\n\n🛑 Animation stopped")

    finally:
        print("\nCleaning up...")
        for dev in devices:
            print(f"  Clearing [{dev.serial}]...")
            dev.close()
        print("✓ All devices cleared and closed\n")


if __name__ == "__main__":
    main()

