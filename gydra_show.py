#!/usr/bin/env python3
"""
GYDRA Show - Dynamic Multi-Device LED Animation
================================================

Динамичное шоу:
1. GYDRA (быстрая прокрутка)
2. ВЗРЫВ
3. GYDRA
4. Цветное моргание

Использование:
    python3 gydra_show.py          # Один раз
    python3 gydra_show.py --loop   # Бесконечный цикл
"""

import sys
import time
import math
import random

from maschine import (
    setup_devices_with_config,
    close_all_devices,
    Color,
    BRIGHTNESS_BRIGHT,
    PAD_COUNT,
    MAX_DEVICES,
)

# === FAST TIMING ===
TEXT_FRAME_DURATION = 0.06  # Быстрая прокрутка
EXPLOSION_FRAME_DURATION = 0.03  # Быстрый взрыв
FLASH_DURATION = 0.04  # Быстрое моргание

# 4x4 Font
FONT = {
    'G': [[0, 1, 1], [1, 0, 0], [1, 0, 1], [0, 1, 1]],
    'Y': [[1, 0, 1], [1, 0, 1], [0, 1, 0], [0, 1, 0]],
    'D': [[1, 1, 0], [1, 0, 1], [1, 0, 1], [1, 1, 0]],
    'R': [[1, 1, 0], [1, 0, 1], [1, 1, 0], [1, 0, 1]],
    'A': [[0, 1, 0], [1, 0, 1], [1, 1, 1], [1, 0, 1]],
    ' ': [[0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0]],
}

# Яркие цвета для эффектов
FLASH_COLORS = [
    Color.WHITE, Color.CYAN, Color.MAGENTA, Color.YELLOW,
    Color.FUCHSIA, Color.ORANGE, Color.LIME, Color.RED,
]


def text_to_bitmap(text):
    columns = []
    for char in text.upper():
        if char in FONT:
            char_data = FONT[char]
            width = len(char_data[0])
            for col_idx in range(width):
                col = [char_data[row][col_idx] for row in range(4)]
                columns.append(col)
            columns.append([0, 0, 0, 0])
    return columns


def bitmap_to_device_patterns(bitmap, offset, num_devices):
    patterns = []
    for device_idx in range(num_devices):
        pattern = [0] * PAD_COUNT
        for col in range(4):
            global_col = offset + (device_idx * 4) + col
            if 0 <= global_col < len(bitmap):
                column = bitmap[global_col]
                for row in range(4):
                    pad_idx = row * 4 + col
                    pattern[pad_idx] = column[row]
        patterns.append(pattern)
    return patterns


def scroll_text(sorted_devices, text, color_idx, loops=1):
    """Fast text scroll"""
    devices = [dev for dev, _ in sorted_devices]
    num_devices = len(devices)

    bitmap = text_to_bitmap(text)
    total_width = len(bitmap)
    display_width = num_devices * 4

    start_offset = -display_width
    end_offset = total_width

    for _ in range(loops):
        offset = start_offset
        while offset < end_offset:
            patterns = bitmap_to_device_patterns(bitmap, offset, num_devices)
            for dev_idx, dev in enumerate(devices):
                dev.set_pattern(patterns[dev_idx], color_idx, BRIGHTNESS_BRIGHT)
            time.sleep(TEXT_FRAME_DURATION)
            offset += 1


def get_pad_positions(num_devices):
    total_cols = num_devices * 4
    center_x = (total_cols - 1) / 2.0
    center_y = 1.5

    positions = []
    for dev_idx in range(num_devices):
        for pad_idx in range(PAD_COUNT):
            row = pad_idx // 4
            col = pad_idx % 4
            global_col = dev_idx * 4 + col
            dist = math.sqrt((global_col - center_x) ** 2 + (row - center_y) ** 2)
            positions.append((dev_idx, pad_idx, dist))

    return positions, max(p[2] for p in positions) if positions else 1


def fast_explosion(sorted_devices):
    """Быстрый взрыв"""
    devices = [dev for dev, _ in sorted_devices]
    num_devices = len(devices)
    positions, max_dist = get_pad_positions(num_devices)

    colors = [Color.WHITE, Color.YELLOW, Color.ORANGE, Color.RED, Color.MAGENTA]

    # Быстрая имплозия
    for t in range(10, -1, -2):
        radius = max_dist * (t / 10.0)
        patterns = [[0] * PAD_COUNT for _ in range(num_devices)]
        for dev_idx, pad_idx, dist in positions:
            if dist <= radius:
                patterns[dev_idx][pad_idx] = 1
        for dev_idx, dev in enumerate(devices):
            dev.set_pattern(patterns[dev_idx], Color.CYAN, BRIGHTNESS_BRIGHT)
        time.sleep(EXPLOSION_FRAME_DURATION)

    # Вспышка в центре
    for dev in devices:
        dev.clear()
    time.sleep(0.02)

    # Быстрый взрыв наружу
    for t in range(0, 15, 2):
        radius = max_dist * (t / 10.0)
        patterns = [[0] * PAD_COUNT for _ in range(num_devices)]
        for dev_idx, pad_idx, dist in positions:
            if dist <= radius:
                patterns[dev_idx][pad_idx] = 1
        color_idx = min(t // 3, len(colors) - 1)
        for dev_idx, dev in enumerate(devices):
            dev.set_pattern(patterns[dev_idx], colors[color_idx], BRIGHTNESS_BRIGHT)
        time.sleep(EXPLOSION_FRAME_DURATION)

    # Финальные вспышки
    for _ in range(4):
        for dev in devices:
            dev.set_all_pads(Color.WHITE, BRIGHTNESS_BRIGHT)
        time.sleep(FLASH_DURATION)
        for dev in devices:
            dev.clear()
        time.sleep(FLASH_DURATION / 2)


def color_strobe(sorted_devices, duration=1.5):
    """Безумное цветное моргание"""
    devices = [dev for dev, _ in sorted_devices]

    start = time.time()
    while time.time() - start < duration:
        color = random.choice(FLASH_COLORS)
        for dev in devices:
            dev.set_all_pads(color, BRIGHTNESS_BRIGHT)
        time.sleep(FLASH_DURATION)
        for dev in devices:
            dev.clear()
        time.sleep(FLASH_DURATION / 2)


def wave_flash(sorted_devices, duration=1.0):
    """Волна вспышек по устройствам"""
    devices = [dev for dev, _ in sorted_devices]
    num_devices = len(devices)

    start = time.time()
    idx = 0
    while time.time() - start < duration:
        color = FLASH_COLORS[idx % len(FLASH_COLORS)]

        # Волна слева направо
        for i in range(num_devices):
            for dev in devices:
                dev.clear()
            devices[i].set_all_pads(color, BRIGHTNESS_BRIGHT)
            time.sleep(FLASH_DURATION)

        idx += 1


def checker_flash(sorted_devices, duration=1.0):
    """Шахматное моргание"""
    devices = [dev for dev, _ in sorted_devices]

    pattern_a = [1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1]
    pattern_b = [0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0]

    start = time.time()
    toggle = False
    while time.time() - start < duration:
        pattern = pattern_b if toggle else pattern_a
        color = random.choice(FLASH_COLORS)

        for dev in devices:
            dev.set_pattern(pattern, color, BRIGHTNESS_BRIGHT)

        time.sleep(FLASH_DURATION * 2)
        toggle = not toggle


def diagonal_wipe(sorted_devices):
    """Диагональная заливка"""
    devices = [dev for dev, _ in sorted_devices]
    num_devices = len(devices)

    total_diags = num_devices * 4 + 4

    # Вперед
    for diag in range(total_diags):
        patterns = [[0] * PAD_COUNT for _ in range(num_devices)]
        for dev_idx in range(num_devices):
            for pad_idx in range(PAD_COUNT):
                row = pad_idx // 4
                col = pad_idx % 4
                global_col = dev_idx * 4 + col
                if global_col + row == diag:
                    patterns[dev_idx][pad_idx] = 1

        color = FLASH_COLORS[diag % len(FLASH_COLORS)]
        for dev_idx, dev in enumerate(devices):
            dev.set_pattern(patterns[dev_idx], color, BRIGHTNESS_BRIGHT)
        time.sleep(FLASH_DURATION)

    # Очистка
    for dev in devices:
        dev.clear()


def run_show(sorted_devices):
    """Динамичное шоу"""
    devices = [dev for dev, _ in sorted_devices]

    # === GYDRA #1 ===
    print("⚡ GYDRA")
    scroll_text(sorted_devices, " GYDRA ", Color.CYAN, loops=1)

    # === EXPLOSION ===
    print("💥 ВЗРЫВ!")
    fast_explosion(sorted_devices)

    # === GYDRA #2 ===
    print("⚡ GYDRA")
    scroll_text(sorted_devices, " GYDRA ", Color.MAGENTA, loops=1)

    # === STROBE ===
    print("🔥 СТРОБ!")
    color_strobe(sorted_devices, duration=1.0)

    # === WAVE ===
    print("🌊 ВОЛНА!")
    wave_flash(sorted_devices, duration=0.8)

    # === CHECKER ===
    print("♟️ ШАХМАТЫ!")
    checker_flash(sorted_devices, duration=0.8)

    # === DIAGONAL ===
    print("↗️ ДИАГОНАЛЬ!")
    diagonal_wipe(sorted_devices)

    # === FINAL BLAST ===
    print("💫 ФИНАЛ!")
    for _ in range(6):
        color = random.choice(FLASH_COLORS)
        for dev in devices:
            dev.set_all_pads(color, BRIGHTNESS_BRIGHT)
        time.sleep(FLASH_DURATION)
        for dev in devices:
            dev.clear()
        time.sleep(FLASH_DURATION / 2)

    for dev in devices:
        dev.clear()


def main():
    loop_mode = '--loop' in sys.argv

    print()
    print("=" * 60)
    print("🐉 GYDRA SHOW — DYNAMIC EDITION")
    print("=" * 60)
    print()

    print("🔍 Поиск контроллеров...")
    sorted_devices = setup_devices_with_config(
        max_count=MAX_DEVICES,
        show_numbers=True,
        show_duration=0.3
    )

    if not sorted_devices:
        print("\n❌ Контроллеры не найдены!")
        print("\n1. Подключите Maschine Mikro MK3")
        print("2. killall NIHardwareAgent")
        return

    print(f"\n✅ Устройств: {len(sorted_devices)}")
    for device, device_num in sorted_devices:
        print(f"   Device {device_num}: {device.serial[:8]}...")
    print()

    if loop_mode:
        print("🔄 Режим: БЕСКОНЕЧНЫЙ ЦИКЛ")
    print("Нажмите Enter для старта...")

    try:
        input()
    except KeyboardInterrupt:
        print("\n🛑 Отменено")
        close_all_devices([dev for dev, _ in sorted_devices])
        return

    try:
        print("\n🚀 ПОЕХАЛИ!\n")

        if loop_mode:
            cycle = 0
            while True:
                cycle += 1
                print(f"\n=== ЦИКЛ {cycle} ===")
                run_show(sorted_devices)
                time.sleep(0.5)
        else:
            run_show(sorted_devices)
            print("\n✅ ГОТОВО!")

    except KeyboardInterrupt:
        print("\n\n🛑 Стоп")

    finally:
        close_all_devices([dev for dev, _ in sorted_devices])
        print("✓ Выход\n")


if __name__ == "__main__":
    main()
