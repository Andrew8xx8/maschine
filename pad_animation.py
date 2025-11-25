#!/usr/bin/env python3
"""
Maschine Mikro MK3 Pad Animation
=================================

Циклическая анимация пэдов по заданным паттернам.
Каждый кадр отображается несколько секунд, затем переход к следующему.
"""

import time
from maschine import find_devices, Color

# Frame duration (seconds)
FRAME_DURATION = 2.0

# Физическая раскладка пэдов (вид сверху):
#    ┌─────────────────────┐
#    │  0   1   2   3  │  <- Верх (дальше от вас)
#    │  4   5   6   7  │
#    │  8   9  10  11  │
#    │ 12  13  14  15  │  <- Низ (ближе к вам)
#    └─────────────────────┘

FRAMES = [
    # Frame 1: Red pattern
    # R · · R
    # · R R ·
    # · R R ·
    # R · · R
    {
        'name': 'Red Pattern',
        'color': Color.RED,
        'pattern': [
            1, 0, 0, 1,  # 0-3 (верх)
            0, 1, 1, 0,  # 4-7
            0, 1, 1, 0,  # 8-11
            1, 0, 0, 1,  # 12-15 (низ)
        ],
    },

    # Frame 2: Green pattern
    # G · · G
    # · G G ·
    # · G · ·
    # G · · ·
    {
        'name': 'Green Pattern',
        'color': Color.GREEN,
        'pattern': [
            1, 0, 0, 1,  # 0-3 (верх)
            0, 1, 1, 0,  # 4-7
            0, 1, 0, 0,  # 8-11
            1, 0, 0, 0,  # 12-15 (низ)
        ],
    },

    # Frame 3: Blue pattern
    # · · B ·
    # B · · B
    # B B B B
    # B · · B
    {
        'name': 'Blue Pattern',
        'color': Color.BLUE,
        'pattern': [
            0, 0, 1, 0,  # 0-3 (верх)
            1, 0, 0, 1,  # 4-7
            1, 1, 1, 1,  # 8-11
            1, 0, 0, 1,  # 12-15 (низ)
        ],
    },
]


def print_pattern_visual(frame):
    """Print visual representation of the pattern"""
    pattern = frame['pattern']
    color_name = frame['name'].split()[0]

    print(f"  {frame['name']}:")
    print()

    # Print in rows of 4 (indices 0-15 map directly to physical layout)
    for row in range(4):
        print("    ", end="")
        for col in range(4):
            pad_idx = row * 4 + col
            value = pattern[pad_idx]

            if value == 0:
                print("·", end=" ")
            else:
                print(color_name[0], end=" ")
        print()
    print()


def main():
    print("🎨 Maschine Mikro MK3 Pad Animation\n")
    print("=" * 50)

    # Find and connect devices
    devices = find_devices(max_count=1)

    if not devices:
        print("❌ No device found")
        print("\nTroubleshooting:")
        print("  1. Connect your Maschine Mikro MK3")
        print("  2. Kill NIHardwareAgent: killall NIHardwareAgent")
        return

    device = devices[0]
    print(f"✓ Connected: {device.serial}\n")

    print("Animation Patterns:")
    print("=" * 50)
    for frame in FRAMES:
        print_pattern_visual(frame)

    print("=" * 50)
    print(f"\nStarting animation (frame duration: {FRAME_DURATION}s)")
    print("Press Ctrl+C to stop\n")

    frame_idx = 0

    try:
        while True:
            frame = FRAMES[frame_idx]

            print(f"[{time.strftime('%H:%M:%S')}] Displaying: {frame['name']}")

            # Display frame using new API
            device.set_pattern(frame['pattern'], frame['color'])

            # Wait for next frame
            time.sleep(FRAME_DURATION)

            # Next frame (cycle)
            frame_idx = (frame_idx + 1) % len(FRAMES)

    except KeyboardInterrupt:
        print("\n\n🛑 Animation stopped")
        print("  Clearing pads...")
        device.clear()

    finally:
        device.close()
        print("  ✓ Device closed\n")


if __name__ == "__main__":
    main()

