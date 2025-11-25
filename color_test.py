#!/usr/bin/env python3
"""
Maschine Mikro MK3 Color Palette Test
======================================

Простой тест всех цветов палитры.
Все пэды мигают одновременно, циклически показывая все доступные цвета.
"""

import time
from maschine import find_devices, Color, BRIGHTNESS_DIM, BRIGHTNESS_NORMAL, BRIGHTNESS_BRIGHT

# Все цвета палитры MK3 (в порядке радуги)
COLORS = [
    ('Red', Color.RED),
    ('Orange', Color.ORANGE),
    ('Light Orange', Color.LIGHT_ORANGE),
    ('Warm Yellow', Color.WARM_YELLOW),
    ('Yellow', Color.YELLOW),
    ('Lime', Color.LIME),
    ('Green', Color.GREEN),
    ('Mint', Color.MINT),
    ('Cyan', Color.CYAN),
    ('Turquoise', Color.TURQUOISE),
    ('Blue', Color.BLUE),
    ('Plum', Color.PLUM),
    ('Violet', Color.VIOLET),
    ('Purple', Color.PURPLE),
    ('Magenta', Color.MAGENTA),
    ('Fuchsia', Color.FUCHSIA),
    ('White', Color.WHITE),
]

# Brightness levels
BRIGHTNESS_LEVELS = [
    ('Dim', BRIGHTNESS_DIM),
    ('Normal', BRIGHTNESS_NORMAL),
    ('Bright', BRIGHTNESS_BRIGHT),
]


def show_color_grid():
    """Show visual color grid"""
    print("\n" + "=" * 70)
    print("ПАЛИТРА ЦВЕТОВ")
    print("=" * 70)

    for idx, (name, color_idx) in enumerate(COLORS, 1):
        print(f"  {color_idx:2d}. {name:<20}")

    print()


def main():
    print("=" * 70)
    print("🎨 Maschine Mikro MK3 - Color Palette Test")
    print("=" * 70)
    print()

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

    # Show color list
    show_color_grid()

    print("=" * 70)
    print("РЕЖИМ ТЕСТА:")
    print("=" * 70)
    print("  1. Цикл по всем цветам (радуга)")
    print("  2. Цикл по яркости")
    print("  3. Бесконечная радуга")
    print("=" * 70)
    print()

    choice = input("Выберите режим (1/2/3) или Enter для режима 3: ").strip()
    if not choice:
        choice = "3"

    print()
    print("Нажмите Ctrl+C для остановки")
    print()

    try:
        if choice == "1":
            # Mode 1: Cycle through all colors once
            print("РЕЖИМ 1: Показ всех цветов\n")

            for color_name, color_idx in COLORS:
                print(f"  {color_idx:2d}. {color_name:<20} ", end="", flush=True)
                device.set_all_pads(color_idx, BRIGHTNESS_BRIGHT)
                time.sleep(1.5)
                print("✓")

            print("\n✅ Тест завершён")

        elif choice == "2":
            # Mode 2: Cycle through brightness levels
            print("РЕЖИМ 2: Тест яркости (Blue)\n")

            for bright_name, bright_val in BRIGHTNESS_LEVELS:
                print(f"  {bright_name:<10} ", end="", flush=True)
                device.set_all_pads(Color.BLUE, bright_val)
                time.sleep(2)
                print("✓")

            print("\n✅ Тест завершён")

        else:
            # Mode 3: Infinite rainbow
            print("РЕЖИМ 3: Бесконечная радуга\n")

            cycle_count = 0

            while True:
                cycle_count += 1
                print(f"Цикл {cycle_count}:")

                for color_name, color_idx in COLORS:
                    print(f"  {color_name:<20}", end="\r", flush=True)
                    device.set_all_pads(color_idx, BRIGHTNESS_BRIGHT)
                    time.sleep(0.5)

                print(" " * 30, end="\r")  # Clear line

    except KeyboardInterrupt:
        print("\n\n🛑 Тест остановлен")

    finally:
        # Clear all pads
        print("\nОчистка...")
        device.clear()
        device.close()
        print("✓ Устройство закрыто\n")


if __name__ == "__main__":
    main()
