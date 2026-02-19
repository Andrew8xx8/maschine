#!/usr/bin/env python3
"""
Maschine Mikro MK3 - Vertical Scrolling Text (8x4 or 8x8)
=========================================================

Бегущая строка на 2 или 4 контроллерах в вертикальной ориентации.

Режимы:
  - 2 контроллера (верх/низ): 4×8 пикселей
  - 4 контроллера (2×2 сетка): 8×8 пикселей

Usage:
    python pad_scroll_vertical.py                    # Default "HELLO"
    python pad_scroll_vertical.py "YOUR TEXT"        # Custom text
    python pad_scroll_vertical.py "HI" --speed 0.1   # Faster scroll
"""

import sys
import time
from pathlib import Path
from maschine import (
    find_devices,
    close_all_devices,
    Color,
    setup_devices_with_config,
    display_logo_on_devices,
)

LOGO_PATH = Path(__file__).parent / "logo.png"

# 4x8 font for vertical display (4 wide, 8 tall)
# Much more readable than 3x4!
FONT_4x8 = {
    'A': [
        [0,1,1,0],
        [1,0,0,1],
        [1,0,0,1],
        [1,1,1,1],
        [1,0,0,1],
        [1,0,0,1],
        [1,0,0,1],
        [0,0,0,0],
    ],
    'B': [
        [1,1,1,0],
        [1,0,0,1],
        [1,0,0,1],
        [1,1,1,0],
        [1,0,0,1],
        [1,0,0,1],
        [1,1,1,0],
        [0,0,0,0],
    ],
    'C': [
        [0,1,1,1],
        [1,0,0,0],
        [1,0,0,0],
        [1,0,0,0],
        [1,0,0,0],
        [1,0,0,0],
        [0,1,1,1],
        [0,0,0,0],
    ],
    'D': [
        [1,1,1,0],
        [1,0,0,1],
        [1,0,0,1],
        [1,0,0,1],
        [1,0,0,1],
        [1,0,0,1],
        [1,1,1,0],
        [0,0,0,0],
    ],
    'E': [
        [1,1,1,1],
        [1,0,0,0],
        [1,0,0,0],
        [1,1,1,0],
        [1,0,0,0],
        [1,0,0,0],
        [1,1,1,1],
        [0,0,0,0],
    ],
    'F': [
        [1,1,1,1],
        [1,0,0,0],
        [1,0,0,0],
        [1,1,1,0],
        [1,0,0,0],
        [1,0,0,0],
        [1,0,0,0],
        [0,0,0,0],
    ],
    'G': [
        [0,1,1,1],
        [1,0,0,0],
        [1,0,0,0],
        [1,0,1,1],
        [1,0,0,1],
        [1,0,0,1],
        [0,1,1,0],
        [0,0,0,0],
    ],
    'H': [
        [1,0,0,1],
        [1,0,0,1],
        [1,0,0,1],
        [1,1,1,1],
        [1,0,0,1],
        [1,0,0,1],
        [1,0,0,1],
        [0,0,0,0],
    ],
    'I': [
        [1,1,1,0],
        [0,1,0,0],
        [0,1,0,0],
        [0,1,0,0],
        [0,1,0,0],
        [0,1,0,0],
        [1,1,1,0],
        [0,0,0,0],
    ],
    'J': [
        [0,0,1,1],
        [0,0,0,1],
        [0,0,0,1],
        [0,0,0,1],
        [1,0,0,1],
        [1,0,0,1],
        [0,1,1,0],
        [0,0,0,0],
    ],
    'K': [
        [1,0,0,1],
        [1,0,1,0],
        [1,1,0,0],
        [1,1,0,0],
        [1,0,1,0],
        [1,0,0,1],
        [1,0,0,1],
        [0,0,0,0],
    ],
    'L': [
        [1,0,0,0],
        [1,0,0,0],
        [1,0,0,0],
        [1,0,0,0],
        [1,0,0,0],
        [1,0,0,0],
        [1,1,1,1],
        [0,0,0,0],
    ],
    'M': [
        [1,0,0,1],
        [1,1,1,1],
        [1,1,1,1],
        [1,0,0,1],
        [1,0,0,1],
        [1,0,0,1],
        [1,0,0,1],
        [0,0,0,0],
    ],
    'N': [
        [1,0,0,1],
        [1,1,0,1],
        [1,1,0,1],
        [1,0,1,1],
        [1,0,1,1],
        [1,0,0,1],
        [1,0,0,1],
        [0,0,0,0],
    ],
    'O': [
        [0,1,1,0],
        [1,0,0,1],
        [1,0,0,1],
        [1,0,0,1],
        [1,0,0,1],
        [1,0,0,1],
        [0,1,1,0],
        [0,0,0,0],
    ],
    'P': [
        [1,1,1,0],
        [1,0,0,1],
        [1,0,0,1],
        [1,1,1,0],
        [1,0,0,0],
        [1,0,0,0],
        [1,0,0,0],
        [0,0,0,0],
    ],
    'Q': [
        [0,1,1,0],
        [1,0,0,1],
        [1,0,0,1],
        [1,0,0,1],
        [1,0,1,1],
        [1,0,0,1],
        [0,1,1,1],
        [0,0,0,0],
    ],
    'R': [
        [1,1,1,0],
        [1,0,0,1],
        [1,0,0,1],
        [1,1,1,0],
        [1,0,1,0],
        [1,0,0,1],
        [1,0,0,1],
        [0,0,0,0],
    ],
    'S': [
        [0,1,1,1],
        [1,0,0,0],
        [1,0,0,0],
        [0,1,1,0],
        [0,0,0,1],
        [0,0,0,1],
        [1,1,1,0],
        [0,0,0,0],
    ],
    'T': [
        [1,1,1,1],
        [0,1,0,0],
        [0,1,0,0],
        [0,1,0,0],
        [0,1,0,0],
        [0,1,0,0],
        [0,1,0,0],
        [0,0,0,0],
    ],
    'U': [
        [1,0,0,1],
        [1,0,0,1],
        [1,0,0,1],
        [1,0,0,1],
        [1,0,0,1],
        [1,0,0,1],
        [0,1,1,0],
        [0,0,0,0],
    ],
    'V': [
        [1,0,0,1],
        [1,0,0,1],
        [1,0,0,1],
        [1,0,0,1],
        [1,0,0,1],
        [0,1,1,0],
        [0,1,1,0],
        [0,0,0,0],
    ],
    'W': [
        [1,0,0,1],
        [1,0,0,1],
        [1,0,0,1],
        [1,0,0,1],
        [1,1,1,1],
        [1,1,1,1],
        [1,0,0,1],
        [0,0,0,0],
    ],
    'X': [
        [1,0,0,1],
        [1,0,0,1],
        [0,1,1,0],
        [0,1,1,0],
        [0,1,1,0],
        [1,0,0,1],
        [1,0,0,1],
        [0,0,0,0],
    ],
    'Y': [
        [1,0,0,1],
        [1,0,0,1],
        [0,1,1,0],
        [0,1,0,0],
        [0,1,0,0],
        [0,1,0,0],
        [0,1,0,0],
        [0,0,0,0],
    ],
    'Z': [
        [1,1,1,1],
        [0,0,0,1],
        [0,0,1,0],
        [0,1,0,0],
        [1,0,0,0],
        [1,0,0,0],
        [1,1,1,1],
        [0,0,0,0],
    ],
    '0': [
        [0,1,1,0],
        [1,0,0,1],
        [1,0,1,1],
        [1,1,0,1],
        [1,0,0,1],
        [1,0,0,1],
        [0,1,1,0],
        [0,0,0,0],
    ],
    '1': [
        [0,1,0,0],
        [1,1,0,0],
        [0,1,0,0],
        [0,1,0,0],
        [0,1,0,0],
        [0,1,0,0],
        [1,1,1,0],
        [0,0,0,0],
    ],
    '2': [
        [0,1,1,0],
        [1,0,0,1],
        [0,0,0,1],
        [0,0,1,0],
        [0,1,0,0],
        [1,0,0,0],
        [1,1,1,1],
        [0,0,0,0],
    ],
    '3': [
        [1,1,1,0],
        [0,0,0,1],
        [0,0,0,1],
        [0,1,1,0],
        [0,0,0,1],
        [0,0,0,1],
        [1,1,1,0],
        [0,0,0,0],
    ],
    '4': [
        [1,0,0,1],
        [1,0,0,1],
        [1,0,0,1],
        [1,1,1,1],
        [0,0,0,1],
        [0,0,0,1],
        [0,0,0,1],
        [0,0,0,0],
    ],
    '5': [
        [1,1,1,1],
        [1,0,0,0],
        [1,1,1,0],
        [0,0,0,1],
        [0,0,0,1],
        [1,0,0,1],
        [0,1,1,0],
        [0,0,0,0],
    ],
    '6': [
        [0,1,1,0],
        [1,0,0,0],
        [1,0,0,0],
        [1,1,1,0],
        [1,0,0,1],
        [1,0,0,1],
        [0,1,1,0],
        [0,0,0,0],
    ],
    '7': [
        [1,1,1,1],
        [0,0,0,1],
        [0,0,1,0],
        [0,0,1,0],
        [0,1,0,0],
        [0,1,0,0],
        [0,1,0,0],
        [0,0,0,0],
    ],
    '8': [
        [0,1,1,0],
        [1,0,0,1],
        [1,0,0,1],
        [0,1,1,0],
        [1,0,0,1],
        [1,0,0,1],
        [0,1,1,0],
        [0,0,0,0],
    ],
    '9': [
        [0,1,1,0],
        [1,0,0,1],
        [1,0,0,1],
        [0,1,1,1],
        [0,0,0,1],
        [0,0,0,1],
        [0,1,1,0],
        [0,0,0,0],
    ],
    ' ': [
        [0,0,0,0],
        [0,0,0,0],
        [0,0,0,0],
        [0,0,0,0],
        [0,0,0,0],
        [0,0,0,0],
        [0,0,0,0],
        [0,0,0,0],
    ],
    '!': [
        [0,1,0,0],
        [0,1,0,0],
        [0,1,0,0],
        [0,1,0,0],
        [0,1,0,0],
        [0,0,0,0],
        [0,1,0,0],
        [0,0,0,0],
    ],
    '.': [
        [0,0,0,0],
        [0,0,0,0],
        [0,0,0,0],
        [0,0,0,0],
        [0,0,0,0],
        [0,0,0,0],
        [0,1,0,0],
        [0,0,0,0],
    ],
    '-': [
        [0,0,0,0],
        [0,0,0,0],
        [0,0,0,0],
        [1,1,1,0],
        [0,0,0,0],
        [0,0,0,0],
        [0,0,0,0],
        [0,0,0,0],
    ],
    ':': [
        [0,0,0,0],
        [0,1,0,0],
        [0,0,0,0],
        [0,0,0,0],
        [0,0,0,0],
        [0,1,0,0],
        [0,0,0,0],
        [0,0,0,0],
    ],
    '?': [
        [0,1,1,0],
        [1,0,0,1],
        [0,0,0,1],
        [0,0,1,0],
        [0,1,0,0],
        [0,0,0,0],
        [0,1,0,0],
        [0,0,0,0],
    ],
    # Heart symbol
    '♥': [
        [0,0,0,0],
        [1,1,1,1],
        [1,1,1,1],
        [1,1,1,1],
        [0,1,1,0],
        [0,1,1,0],
        [0,0,0,0],
        [0,0,0,0],
    ],
}


# Rainbow colors for animation
RAINBOW = [
    Color.RED,
    Color.ORANGE,
    Color.YELLOW,
    Color.LIME,
    Color.GREEN,
    Color.MINT,
    Color.CYAN,
    Color.BLUE,
    Color.PURPLE,
    Color.MAGENTA,
]


def text_to_columns(text: str) -> list:
    """Convert text to list of columns (each column is 8 pixels tall)."""
    columns = []

    for char in text.upper():
        if char in FONT_4x8:
            char_data = FONT_4x8[char]
            # Each character is 4 columns wide
            for col in range(4):
                column = [char_data[row][col] for row in range(8)]
                columns.append(column)
            # Add 1-pixel gap between characters
            columns.append([0] * 8)
        else:
            # Unknown char = space (4 cols + 1 gap)
            for _ in range(5):
                columns.append([0] * 8)

    # Remove trailing gap
    if columns and columns[-1] == [0] * 8:
        columns.pop()

    return columns


def set_vertical_grid(devices, bitmap_8x8, color, brightness=0x7f):
    """
    Set 8x8 grid on 4 devices arranged as 2x2.

    Layout (looking at devices):
        [Dev0] [Dev1]   <- top row (rows 0-3)
        [Dev2] [Dev3]   <- bottom row (rows 4-7)

    Each device shows 4x4 portion of the 8x8 grid.
    """
    # Device positions in 2x2 grid:
    # devices[0] = top-left (cols 0-3, rows 0-3)
    # devices[1] = top-right (cols 4-7, rows 0-3)
    # devices[2] = bottom-left (cols 0-3, rows 4-7)
    # devices[3] = bottom-right (cols 4-7, rows 4-7)

    device_map = [
        (0, 0, 0),  # device 0: col_offset=0, row_offset=0
        (1, 4, 0),  # device 1: col_offset=4, row_offset=0
        (2, 0, 4),  # device 2: col_offset=0, row_offset=4
        (3, 4, 4),  # device 3: col_offset=4, row_offset=4
    ]

    for dev_idx, col_off, row_off in device_map:
        if dev_idx >= len(devices):
            continue

        pattern = [0] * 16

        for local_row in range(4):
            for local_col in range(4):
                global_row = row_off + local_row
                global_col = col_off + local_col

                # Check bounds and if pixel is lit
                if (global_col < len(bitmap_8x8) and
                    global_row < len(bitmap_8x8[global_col]) and
                    bitmap_8x8[global_col][global_row]):
                    # Pad index: row * 4 + col
                    pad_idx = local_row * 4 + local_col
                    pattern[pad_idx] = 1

        devices[dev_idx].set_pattern(pattern, color, brightness)


def scroll_text(devices, text, base_color=Color.CYAN, speed=0.12, rainbow=False):
    """Scroll text horizontally across 8x8 grid."""
    # Add padding for smooth scroll in/out
    padded_text = "    " + text + "    "
    columns = text_to_columns(padded_text)

    total_cols = len(columns)
    color_idx = 0

    print(f"📜 Бегущая строка: '{text}' ({total_cols} колонок)")
    print("   Ctrl+C для остановки\n")

    try:
        while True:
            for offset in range(total_cols - 7):
                # Extract 8 columns starting at offset
                bitmap_8x8 = columns[offset:offset + 8]

                # Pad if needed
                while len(bitmap_8x8) < 8:
                    bitmap_8x8.append([0] * 8)

                # Choose color
                if rainbow:
                    color = RAINBOW[color_idx % len(RAINBOW)]
                    color_idx += 1
                else:
                    color = base_color

                set_vertical_grid(devices, bitmap_8x8, color)
                time.sleep(speed)

    except KeyboardInterrupt:
        pass


def animation_wave(devices, duration=10):
    """Wave animation across 8x8 grid."""
    import math

    print("🌊 Волна")
    start = time.time()
    frame = 0

    while time.time() - start < duration:
        bitmap = []
        for col in range(8):
            column = [0] * 8
            # Sine wave
            wave_y = int(3.5 + 3 * math.sin((col + frame) * 0.5))
            if 0 <= wave_y < 8:
                column[wave_y] = 1
                if wave_y > 0:
                    column[wave_y - 1] = 1
            bitmap.append(column)

        color = RAINBOW[frame % len(RAINBOW)]
        set_vertical_grid(devices, bitmap, color)
        frame += 1
        time.sleep(0.08)


def animation_rain(devices, duration=10):
    """Rain drops falling down."""
    import random

    print("🌧️  Дождь")
    start = time.time()

    # Drops: list of (col, row) positions
    drops = [(random.randint(0, 7), random.randint(-8, 0)) for _ in range(6)]

    while time.time() - start < duration:
        bitmap = [[0] * 8 for _ in range(8)]

        for i, (col, row) in enumerate(drops):
            if 0 <= row < 8:
                bitmap[col][row] = 1

            # Move drop down
            drops[i] = (col, row + 1)

            # Reset drop if off screen
            if row > 8:
                drops[i] = (random.randint(0, 7), random.randint(-3, 0))

        set_vertical_grid(devices, bitmap, Color.CYAN)
        time.sleep(0.1)


def animation_spiral(devices, duration=10):
    """Spiral from center outward."""
    print("🌀 Спираль")
    start = time.time()

    # Generate spiral order from center
    center = 3.5
    positions = []
    for col in range(8):
        for row in range(8):
            dist = ((col - center) ** 2 + (row - center) ** 2) ** 0.5
            positions.append((col, row, dist))
    positions.sort(key=lambda x: x[2])

    while time.time() - start < duration:
        for count in range(len(positions) + 10):
            bitmap = [[0] * 8 for _ in range(8)]

            for i in range(min(count, len(positions))):
                col, row, _ = positions[i]
                bitmap[col][row] = 1

            color = RAINBOW[(count // 4) % len(RAINBOW)]
            set_vertical_grid(devices, bitmap, color)
            time.sleep(0.05)

            if time.time() - start >= duration:
                break


def animation_heartbeat(devices, duration=10):
    """Pulsing heart."""
    print("💓 Сердце")
    start = time.time()

    # Heart pattern 8x8
    heart = [
        [0,1,1,0,0,1,1,0],
        [1,1,1,1,1,1,1,1],
        [1,1,1,1,1,1,1,1],
        [1,1,1,1,1,1,1,1],
        [0,1,1,1,1,1,1,0],
        [0,0,1,1,1,1,0,0],
        [0,0,0,1,1,0,0,0],
        [0,0,0,0,0,0,0,0],
    ]

    # Transpose to column format
    heart_cols = [[heart[row][col] for row in range(8)] for col in range(8)]

    frame = 0
    while time.time() - start < duration:
        # Pulse between red and magenta
        colors = [Color.RED, Color.RED, Color.MAGENTA, Color.RED]
        color = colors[frame % len(colors)]

        # Brightness pulse
        brightness = 0x7f if (frame % 4) < 2 else 0x3f

        set_vertical_grid(devices, heart_cols, color, brightness)
        frame += 1
        time.sleep(0.25)


def main():
    text = "HELLO"
    speed = 0.12
    rainbow = False
    animation = None  # None = scroll text, or specific animation name

    if len(sys.argv) > 1:
        if sys.argv[1] == "--help":
            print(__doc__)
            print("\nОпции:")
            print("  --speed N     Скорость прокрутки в секундах (default: 0.12)")
            print("  --rainbow     Радужные цвета")
            print("  --demo        Демо всех анимаций")
            print("  --heart       Только сердце 💓")
            print("  --wave        Только волна 🌊")
            print("  --rain        Только дождь 🌧️")
            print("  --spiral      Только спираль 🌀")
            return
        if sys.argv[1] not in ("--demo", "--heart", "--wave", "--rain", "--spiral"):
            text = sys.argv[1]

    if "--speed" in sys.argv:
        idx = sys.argv.index("--speed")
        if idx + 1 < len(sys.argv):
            speed = float(sys.argv[idx + 1])

    if "--rainbow" in sys.argv:
        rainbow = True

    # Check for specific animations
    if "--demo" in sys.argv:
        animation = "demo"
    elif "--heart" in sys.argv:
        animation = "heart"
    elif "--wave" in sys.argv:
        animation = "wave"
    elif "--rain" in sys.argv:
        animation = "rain"
    elif "--spiral" in sys.argv:
        animation = "spiral"

    # Find devices
    print("🔍 Поиск устройств...")
    sorted_devices = setup_devices_with_config(max_count=4)

    if len(sorted_devices) < 4:
        print(f"⚠️  Найдено {len(sorted_devices)} устройств, нужно 4 для полного 8x8")
        if len(sorted_devices) < 2:
            print("❌ Минимум 2 устройства для работы")
            close_all_devices([d for d, _ in sorted_devices])
            return

    devices = [d for d, _ in sorted_devices]
    print(f"✅ Подключено {len(devices)} устройств")
    print(f"   Сетка: {'8×8' if len(devices) >= 4 else '4×8'}")

    # Display logo
    if LOGO_PATH.exists():
        display_logo_on_devices(devices, LOGO_PATH)

    try:
        if animation == "demo":
            print("\n🎬 Демо анимаций (Ctrl+C для остановки)\n")
            while True:
                animation_wave(devices, duration=8)
                animation_rain(devices, duration=8)
                animation_spiral(devices, duration=8)
                animation_heartbeat(devices, duration=8)
                scroll_text(devices, "MASCHINE", rainbow=True, speed=0.1)
        elif animation == "heart":
            print("\n💓 Сердце (Ctrl+C для остановки)\n")
            while True:
                animation_heartbeat(devices, duration=999999)
        elif animation == "wave":
            print("\n🌊 Волна (Ctrl+C для остановки)\n")
            while True:
                animation_wave(devices, duration=999999)
        elif animation == "rain":
            print("\n🌧️  Дождь (Ctrl+C для остановки)\n")
            while True:
                animation_rain(devices, duration=999999)
        elif animation == "spiral":
            print("\n🌀 Спираль (Ctrl+C для остановки)\n")
            while True:
                animation_spiral(devices, duration=999999)
        else:
            scroll_text(devices, text, speed=speed, rainbow=rainbow)

    except KeyboardInterrupt:
        print("\n\n🛑 Остановлено")

    finally:
        print("Очистка...")
        for dev in devices:
            dev.clear()
        close_all_devices(devices)
        print("✓ Готово")


if __name__ == "__main__":
    main()

