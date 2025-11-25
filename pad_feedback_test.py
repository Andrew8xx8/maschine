#!/usr/bin/env python3
"""
Maschine Mikro MK3 Pad Feedback Test
=====================================

Тест обратной связи: нажатый пэд загорается, отпущенный гаснет.
"""

import hid
import time
import os
import sys

VENDOR_ID = 0x17cc
PRODUCT_ID = 0x1700

LED_BUFFER_SIZE = 81
PAD_OFFSET = 40

# Цвет для подсветки
FEEDBACK_COLOR = 11  # Blue
BRIGHTNESS_BRIGHT = 0x7f


def init_device(device):
    """Initialize device"""
    client_id = os.urandom(8)
    device.write([0x03, 0x01] + list(client_id) + [0x00] * 54)
    time.sleep(0.05)

    sequences = [
        [0x01, 0x00, 0x00, 0x02, 0x01, 0x00, 0x00, 0x00] + [0x00] * 56,
        [0x04, 0x00, 0x01, 0x00, 0x00, 0x00] + [0x00] * 58,
        [0x80, 0x00] + [0x00] * 62,
    ]

    for seq in sequences:
        device.write(seq)
        time.sleep(0.03)

    device.set_nonblocking(True)
    time.sleep(0.1)


def decode_pad_events(data):
    """
    Decode pad events from HID report 0x02

    Returns:
        List of (pad_index, event_type, velocity) tuples
    """
    if not data or data[0] != 0x02:
        return []

    events = []

    # Parse pad event triplets
    for i in range(1, len(data), 3):
        pad_idx = data[i]
        event_byte = data[i + 1]
        vel_low = data[i + 2]

        # Stop at padding
        if i > 1 and pad_idx == 0 and event_byte == 0 and vel_low == 0:
            break

        event_type = event_byte & 0xf0
        velocity_12bit = ((event_byte & 0x0f) << 8) | vel_low
        velocity = velocity_12bit >> 5  # Convert to MIDI range (0-127)

        # Event types (from MK3 driver):
        # 0x00 = PressOn
        # 0x10 = NoteOn
        # 0x20 = PressOff
        # 0x30 = NoteOff
        # 0x40 = Aftertouch

        is_press = (event_type == 0x00) or (event_type == 0x10)  # PressOn or NoteOn
        is_release = (event_type == 0x20) or (event_type == 0x30)  # PressOff or NoteOff

        events.append({
            'pad': pad_idx,
            'event_type': event_type,
            'velocity': velocity,
            'is_press': is_press,
            'is_release': is_release,
        })

    return events


def set_pad_light(led_buffer, pad_idx, color_idx, on=True):
    """Set single pad light on or off"""
    if on:
        value = (color_idx << 2) | (BRIGHTNESS_BRIGHT & 0b11)
    else:
        value = 0

    led_buffer[PAD_OFFSET + pad_idx] = value


def main():
    print("=" * 70)
    print("🎹 Maschine Mikro MK3 - Pad Feedback Test")
    print("=" * 70)
    print()

    # Find device
    devices = [d for d in hid.enumerate()
               if d['vendor_id'] == VENDOR_ID and d['product_id'] == PRODUCT_ID]

    if not devices:
        print("❌ No device found")
        print("\nTroubleshooting:")
        print("  1. Connect your Maschine Mikro MK3")
        print("  2. Kill NIHardwareAgent: killall NIHardwareAgent")
        return

    # Connect to first device
    dev = hid.device()
    dev.open_path(devices[0]['path'])
    serial = devices[0]['serial_number']
    print(f"✓ Connected: {serial}\n")

    # Initialize
    print("Initializing device...")
    init_device(dev)
    print("✓ Device initialized\n")

    # Create LED buffer
    led_buffer = [0x00] * LED_BUFFER_SIZE
    led_buffer[0] = 0x80  # Report ID

    print("=" * 70)
    print("ТЕСТ ОБРАТНОЙ СВЯЗИ")
    print("=" * 70)
    print()
    print("Нажимайте на пэды - они будут загораться!")
    print("Отпустите пэд - он погаснет.")
    print()
    print("Статистика будет показана ниже.")
    print("Нажмите Ctrl+C для остановки")
    print()
    print("-" * 70)
    print()

    # Track pad states
    pad_states = [False] * 16  # True = pressed/lit
    total_presses = 0
    pad_press_counts = [0] * 16

    try:
        while True:
            # Read HID data
            data = dev.read(64, timeout_ms=10)

            if data:
                events = decode_pad_events(data)

                for event in events:
                    pad_idx = event['pad']

                    if event['is_press']:
                        # Pad pressed - light it up
                        if not pad_states[pad_idx]:
                            pad_states[pad_idx] = True
                            set_pad_light(led_buffer, pad_idx, FEEDBACK_COLOR, on=True)
                            dev.write(led_buffer)

                            total_presses += 1
                            pad_press_counts[pad_idx] += 1

                            print(f"🔵 Pad {pad_idx + 1:2d} ON  (velocity: {event['velocity']:3d})  "
                                  f"[Total: {total_presses}]")

                    elif event['is_release']:
                        # Pad released - turn it off
                        if pad_states[pad_idx]:
                            pad_states[pad_idx] = False
                            set_pad_light(led_buffer, pad_idx, FEEDBACK_COLOR, on=False)
                            dev.write(led_buffer)

                            print(f"⚫ Pad {pad_idx + 1:2d} OFF")

            time.sleep(0.001)

    except KeyboardInterrupt:
        print("\n\n" + "=" * 70)
        print("СТАТИСТИКА")
        print("=" * 70)
        print()
        print(f"Всего нажатий: {total_presses}")
        print()

        if total_presses > 0:
            print("Нажатия по пэдам:")
            for pad_idx in range(16):
                if pad_press_counts[pad_idx] > 0:
                    percent = (pad_press_counts[pad_idx] / total_presses) * 100
                    bar = "█" * int(percent / 5)
                    print(f"  Pad {pad_idx + 1:2d}: {pad_press_counts[pad_idx]:3d} раз  {bar:20s} ({percent:5.1f}%)")

        print()
        print("🛑 Тест остановлен")

    finally:
        # Clear all pads
        print("\nОчистка...")
        for i in range(16):
            led_buffer[PAD_OFFSET + i] = 0
        dev.write(led_buffer)
        dev.close()
        print("✓ Устройство закрыто\n")


if __name__ == "__main__":
    main()

