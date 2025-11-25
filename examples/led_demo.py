#!/usr/bin/env python3
"""
LED Control Demo for Maschine Mikro MK3
========================================

Demonstrates the color palette and brightness control.
Shows all 17 colors and 3 brightness levels.
"""

import hid
import time
import os

VENDOR_ID = 0x17cc
PRODUCT_ID = 0x1700

# LED configuration
LED_BUFFER_SIZE = 81
PAD_OFFSET = 40

# Color palette
COLORS = {
    'Red': 1, 'Orange': 2, 'Yellow': 5, 'Lime': 6,
    'Green': 7, 'Mint': 8, 'Cyan': 9, 'Turquoise': 10,
    'Blue': 11, 'Plum': 12, 'Violet': 13, 'Purple': 14,
    'Magenta': 15, 'Fuchsia': 16, 'White': 17
}

# Brightness levels
BRIGHTNESS = {'Dim': 0x7c, 'Normal': 0x7e, 'Bright': 0x7f}

def init_device(device):
    """Initialize device with handshakes"""
    client_id = os.urandom(8)
    device.write([0x03, 0x01] + list(client_id) + [0x00] * 54)
    time.sleep(0.1)

    for seq in [
        [0x01, 0x00, 0x00, 0x02, 0x01, 0x00, 0x00, 0x00] + [0x00] * 56,
        [0x04, 0x00, 0x01, 0x00, 0x00, 0x00] + [0x00] * 58,
    ]:
        device.write(seq)
        time.sleep(0.05)

    device.set_nonblocking(True)

def set_pad(buffer, pad_idx, color_idx, brightness):
    """Set pad color in LED buffer"""
    value = (color_idx << 2) | (brightness & 0b11) if brightness else 0
    buffer[PAD_OFFSET + pad_idx] = value

def main():
    print("🎨 Maschine Mikro MK3 LED Demo\n")

    # Find and connect
    devices = [d for d in hid.enumerate()
               if d['vendor_id'] == VENDOR_ID and d['product_id'] == PRODUCT_ID]

    if not devices:
        print("❌ No device found")
        return

    dev = hid.device()
    dev.open_path(devices[0]['path'])
    print(f"✓ Connected: {devices[0]['serial_number']}\n")

    init_device(dev)

    # Create LED buffer
    led_buffer = [0x00] * LED_BUFFER_SIZE
    led_buffer[0] = 0x80  # Report ID

    print("=" * 50)
    print("Color Palette Demo")
    print("=" * 50)

    color_list = list(COLORS.items())

    # Show colors on first 15 pads (3 rounds of 5 colors)
    for round_idx in range(3):
        start = round_idx * 5
        end = min(start + 5, len(color_list))

        for i in range(start, end):
            name, color_idx = color_list[i]
            pad = i % 16

            # Clear previous
            if pad == 0:
                for p in range(16):
                    set_pad(led_buffer, p, 0, 0)

            set_pad(led_buffer, pad, color_idx, BRIGHTNESS['Normal'])
            dev.write(led_buffer)
            print(f"  Pad {pad + 1:2d}: {name}")
            time.sleep(0.4)

    time.sleep(1)

    print("\n" + "=" * 50)
    print("Brightness Levels Demo")
    print("=" * 50)

    for bright_name, bright_val in BRIGHTNESS.items():
        print(f"\n{bright_name} brightness:")

        # Set all pads to Blue at this brightness
        for pad in range(16):
            set_pad(led_buffer, pad, COLORS['Blue'], bright_val)

        dev.write(led_buffer)
        time.sleep(1.5)

    # Clear all
    print("\nClearing...")
    for pad in range(16):
        set_pad(led_buffer, pad, 0, 0)
    dev.write(led_buffer)

    dev.close()
    print("\n✅ Demo complete!\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted")

