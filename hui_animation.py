#!/usr/bin/env python3
"""
Maschine Mikro MK3 Multi-Device Animation
==========================================

Анимация на всех подключенных устройствах (до 4 штук).
Кадры циклически "сдвигаются" между устройствами, цвета меняются каждый кадр.
"""

import hid
import time
import os
import sys
import threading
import random

VENDOR_ID = 0x17cc
PRODUCT_ID = 0x1700
MAX_DEVICES = 4

# LED configuration
LED_BUFFER_SIZE = 81
PAD_OFFSET = 40

# All available colors from MK3 palette
COLORS = [
    ('Red', 1),
    ('Orange', 2),
    ('Light Orange', 3),
    ('Warm Yellow', 4),
    ('Yellow', 5),
    ('Lime', 6),
    ('Green', 7),
    ('Mint', 8),
    ('Cyan', 9),
    ('Turquoise', 10),
    ('Blue', 11),
    ('Plum', 12),
    ('Violet', 13),
    ('Purple', 14),
    ('Magenta', 15),
    ('Fuchsia', 16),
    ('White', 17),
]

COLOR_OFF = 0
BRIGHTNESS_BRIGHT = 0x7f

# Frame duration (seconds)
FRAME_DURATION = 2.0

# Pattern templates (0 = off, 1 = on)
# Физическая раскладка: 0-3 (верх), 4-7, 8-11, 12-15 (низ)
PATTERN_TEMPLATES = [
    # Pattern 1: Corners
    {
        'name': 'Corners',
        'template': [
            1, 0, 0, 1,  # 0-3
            0, 1, 1, 0,  # 4-7
            0, 1, 1, 0,  # 8-11
            1, 0, 0, 1,  # 12-15
        ],
    },

    # Pattern 2: Diagonal
    {
        'name': 'Diagonal',
        'template': [
            1, 0, 0, 1,  # 0-3
            0, 1, 1, 0,  # 4-7
            0, 1, 0, 0,  # 8-11
            1, 0, 0, 0,  # 12-15
        ],
    },

    # Pattern 3: Cross
    {
        'name': 'Cross',
        'template': [
            0, 0, 1, 0,  # 0-3
            1, 0, 0, 1,  # 4-7
            1, 1, 1, 1,  # 8-11
            1, 0, 0, 1,  # 12-15
        ],
    },

    # Pattern 4: Empty (для ротации)
    {
        'name': 'Empty',
        'template': [0] * 16,
    },
]


class Device:
    """Wrapper for HID device"""
    def __init__(self, device_info):
        self.info = device_info
        self.serial = device_info['serial_number']
        self.device = None
        self.led_buffer = [0x00] * LED_BUFFER_SIZE
        self.led_buffer[0] = 0x80
        self.lock = threading.Lock()

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

            # Clear all pads after init
            time.sleep(0.1)
            for i in range(16):
                self.led_buffer[PAD_OFFSET + i] = 0
            self.device.write(self.led_buffer)

            return True

        except Exception as e:
            print(f"[{self.serial}] Error connecting: {e}")
            return False

    def set_pattern(self, template, color_idx):
        """Set pattern with color"""
        with self.lock:
            for pad_idx in range(16):
                if template[pad_idx] == 0:
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
        with self.lock:
            for i in range(16):
                self.led_buffer[PAD_OFFSET + i] = 0
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


def print_pattern_preview(template, color_name):
    """Print pattern preview"""
    for row in range(4):
        print("    ", end="")
        for col in range(4):
            pad_idx = row * 4 + col
            if template[pad_idx] == 1:
                print(color_name[0], end=" ")
            else:
                print("·", end=" ")
        print()


def identify_device(device, identifier_color_idx):
    """Light up device with identifier color"""
    # Light all pads with the color
    with device.lock:
        for pad_idx in range(16):
            value = (identifier_color_idx << 2) | (BRIGHTNESS_BRIGHT & 0b11)
            device.led_buffer[PAD_OFFSET + pad_idx] = value

        try:
            device.device.write(device.led_buffer)
            time.sleep(0.05)  # Small delay to ensure write completes
        except Exception as e:
            print(f"[{device.serial}] Write error: {e}")


def setup_device_order(devices):
    """Interactive setup to define device order"""
    print("\n" + "=" * 70)
    print("НАСТРОЙКА ПОРЯДКА УСТРОЙСТВ")
    print("=" * 70)
    print()

    # If only one device, skip setup
    if len(devices) == 1:
        print("Подключено только 1 устройство - настройка порядка не требуется\n")
        return devices

    print("Я буду подсвечивать каждое устройство разными цветами.")
    print("Вы определяете номер позиции для каждого устройства (1, 2, 3, 4).")
    print()
    print("Позиции:")
    print("  1 = первое устройство (начало анимации)")
    print("  2 = второе устройство")
    if len(devices) > 2:
        print("  3 = третье устройство")
    if len(devices) > 3:
        print("  4 = четвертое устройство")
    print()

    # Option to skip
    skip = input("Пропустить настройку и использовать автоматический порядок? (y/n): ").strip().lower()
    if skip in ['y', 'yes', 'д', 'да']:
        print("\n✓ Используется автоматический порядок\n")
        return devices

    print()

    # Colors for identification
    identifier_colors = [
        ('Red', 1),
        ('Green', 7),
        ('Blue', 11),
        ('Yellow', 5),
    ]

    device_positions = {}  # device -> position (1-4)
    used_positions = set()

    for idx, dev in enumerate(devices):
        print("=" * 70)
        color_name, color_idx = identifier_colors[idx % len(identifier_colors)]

        print(f"\nПодсвечиваю устройство: {dev.serial}")
        print(f"Цвет: {color_name.upper()}")
        print()

        # Light up this device
        identify_device(dev, color_idx)

        # Give time to see the device
        time.sleep(0.5)

        while True:
            try:
                available = [i for i in range(1, len(devices) + 1) if i not in used_positions]
                print(f"Доступные позиции: {', '.join(map(str, available))}")
                position = input(f"Введите позицию для этого устройства (1-{len(devices)}): ").strip()

                position = int(position)

                if position < 1 or position > len(devices):
                    print(f"❌ Позиция должна быть от 1 до {len(devices)}")
                    continue

                if position in used_positions:
                    print(f"❌ Позиция {position} уже занята")
                    continue

                device_positions[dev] = position
                used_positions.add(position)

                print(f"✓ Устройство {dev.serial} -> Позиция {position}")

                # Clear device
                time.sleep(0.3)
                dev.clear()
                time.sleep(0.2)

                break

            except ValueError:
                print("❌ Введите число")
            except KeyboardInterrupt:
                print("\n\n❌ Прервано пользователем")
                for d in devices:
                    d.clear()
                    d.close()
                sys.exit(0)

        print()

    # Sort devices by position
    sorted_devices = sorted(devices, key=lambda d: device_positions[d])

    print("=" * 70)
    print("ПОРЯДОК УСТРОЙСТВ:")
    print("=" * 70)
    for i, dev in enumerate(sorted_devices, 1):
        print(f"  Позиция {i}: {dev.serial}")
    print()

    # Confirm with visual preview
    print("Показываю порядок визуально (пэды загорятся по очереди)...")
    time.sleep(1)

    for i, dev in enumerate(sorted_devices, 1):
        # Light device with its position number pattern
        # Show position number as lit pads
        template = [0] * 16
        for j in range(min(i * 4, 16)):  # Light up rows based on position
            template[j] = 1
        dev.set_pattern(template, 17)  # White
        print(f"  Позиция {i} светится...")
        time.sleep(1.5)
        dev.clear()
        time.sleep(0.3)

    print()
    confirm = input("Порядок правильный? (y/n): ").strip().lower()
    if confirm not in ['y', 'yes', 'д', 'да']:
        print("\n⚠️  Перезапустите программу для настройки заново\n")
        for d in devices:
            d.close()
        sys.exit(0)

    print("✓ Порядок подтверждён!\n")
    return sorted_devices


def main():
    print("=" * 70)
    print("🎨 Maschine Mikro MK3 Multi-Device Animation")
    print("=" * 70)
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

    print(f"✓ Found {len(device_infos)} device(s)\n")

    # Connect devices
    devices = []
    for info in device_infos:
        dev = Device(info)
        if dev.connect():
            devices.append(dev)
            print(f"  [{dev.serial}] Connected")

    if not devices:
        print("\n❌ Failed to connect to any devices")
        return

    print(f"\n✓ Successfully connected to {len(devices)} device(s)")

    # Small delay to ensure all devices are fully ready
    print("\nПодготовка устройств...")
    time.sleep(1)

    # Setup device order interactively
    devices = setup_device_order(devices)

    # Show info
    print("=" * 70)
    print("Animation Info:")
    print("=" * 70)
    print(f"  Devices: {len(devices)}")
    print(f"  Patterns: {len(PATTERN_TEMPLATES)}")
    print(f"  Frame Duration: {FRAME_DURATION}s")
    print(f"  Available Colors: {len(COLORS)}")
    print()
    print("Pattern Templates:")
    for i, pattern in enumerate(PATTERN_TEMPLATES):
        print(f"\n  {i+1}. {pattern['name']}:")
        print_pattern_preview(pattern['template'], "X")
    print()
    print("=" * 70)
    print(f"\nStarting animation on {len(devices)} device(s)")
    print("Patterns rotate between devices, colors change randomly")
    print("Press Ctrl+C to stop\n")

    time.sleep(1)

    # Animation state
    device_pattern_offset = 0  # Для ротации паттернов между девайсами

    try:
        while True:
            # Выбираем случайные цвета для каждого паттерна (кроме Empty)
            pattern_colors = {}
            for i in range(len(PATTERN_TEMPLATES) - 1):
                color_name, color_idx = random.choice(COLORS)
                pattern_colors[i] = (color_name, color_idx)

            # Для каждого девайса назначаем паттерн с ротацией
            timestamp = time.strftime('%H:%M:%S')
            print(f"[{timestamp}] Frame {device_pattern_offset + 1}:")

            for dev_idx, dev in enumerate(devices):
                # Определяем какой паттерн показывать на этом девайсе
                pattern_idx = (dev_idx + device_pattern_offset) % len(PATTERN_TEMPLATES)
                pattern = PATTERN_TEMPLATES[pattern_idx]

                if pattern['name'] == 'Empty':
                    dev.clear()
                    print(f"  Позиция {dev_idx+1} [{dev.serial}]: Empty")
                else:
                    color_name, color_idx = pattern_colors[pattern_idx]
                    dev.set_pattern(pattern['template'], color_idx)
                    print(f"  Позиция {dev_idx+1} [{dev.serial}]: {pattern['name']} ({color_name})")

            print()

            # Wait for next frame
            time.sleep(FRAME_DURATION)

            # Rotate pattern offset
            device_pattern_offset = (device_pattern_offset + 1) % len(PATTERN_TEMPLATES)

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

