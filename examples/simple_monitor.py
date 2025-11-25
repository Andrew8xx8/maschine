#!/usr/bin/env python3
"""
Simple Maschine Mikro MK3 Monitor
===================================

Minimal example showing basic pad monitoring without LED control.
Great starting point for custom implementations.
"""

import hid
import time
import os

VENDOR_ID = 0x17cc
PRODUCT_ID = 0x1700

def init_device(device):
    """Send initialization handshake"""
    # NHL Registration
    client_id = os.urandom(8)
    device.write([0x03, 0x01] + list(client_id) + [0x00] * 54)
    time.sleep(0.1)

    # Wake-up sequences
    sequences = [
        [0x01, 0x00, 0x00, 0x02, 0x01, 0x00, 0x00, 0x00] + [0x00] * 56,
        [0x04, 0x00, 0x01, 0x00, 0x00, 0x00] + [0x00] * 58,
        [0x80, 0x00] + [0x00] * 62,
    ]
    for seq in sequences:
        device.write(seq)
        time.sleep(0.05)

    device.set_nonblocking(True)

def decode_pads(data):
    """Extract pad events from HID report"""
    if not data or data[0] != 0x02:
        return []

    events = []
    for i in range(1, len(data), 3):
        pad_idx = data[i]
        event_type = data[i + 1] & 0xf0
        velocity_12bit = ((data[i + 1] & 0x0f) << 8) | data[i + 2]

        # Stop at padding
        if i > 1 and pad_idx == 0 and event_type == 0 and velocity_12bit == 0:
            break

        # Convert to MIDI velocity (0-127)
        velocity = velocity_12bit >> 5

        events.append({
            'pad': pad_idx,
            'type': 'press' if event_type == 0x90 else 'release',
            'velocity': velocity
        })

    return events

def main():
    print("🎛️  Simple Maschine Mikro MK3 Monitor\n")

    # Find device
    devices = [d for d in hid.enumerate()
               if d['vendor_id'] == VENDOR_ID and d['product_id'] == PRODUCT_ID]

    if not devices:
        print("❌ No device found")
        return

    # Connect
    dev = hid.device()
    dev.open_path(devices[0]['path'])
    serial = devices[0]['serial_number']
    print(f"✓ Connected: {serial}\n")

    # Initialize
    init_device(dev)
    print("✓ Device initialized")
    print("\nPress pads (Ctrl+C to exit)...\n")

    # Event loop
    try:
        while True:
            data = dev.read(64, timeout_ms=10)
            if data:
                events = decode_pads(data)
                for evt in events:
                    print(f"  Pad {evt['pad'] + 1:2d}: {evt['type']:7s} velocity={evt['velocity']:3d}")
            time.sleep(0.001)
    except KeyboardInterrupt:
        print("\n\nStopped")
    finally:
        dev.close()

if __name__ == "__main__":
    main()

