#!/usr/bin/env python3
"""
🔆 BRIGHTNESS TEST - Тест интенсивности цветов
==============================================

Показывает один цвет с разными уровнями яркости (Dim, Normal, Bright)
чтобы визуально оценить разницу.
"""

import time
import sys
from maschine import (
    find_devices,
    Color,
    BRIGHTNESS_DIM,
    BRIGHTNESS_NORMAL,
    BRIGHTNESS_BRIGHT,
)


# Интересные цвета для теста
TEST_COLORS = [
    ('RED', Color.RED, 'Чистый красный (1 LED)'),
    ('ORANGE', Color.ORANGE, 'Оранжевый (красный + зеленый)'),
    ('MAGENTA', Color.MAGENTA, 'Маджента (красный + синий)'),
    ('FUCHSIA', Color.FUCHSIA, 'Фуксия (ярко-розовый)'),
    ('CYAN', Color.CYAN, 'Бирюзовый (зеленый + синий)'),
    ('BLUE', Color.BLUE, 'Синий (самый яркий LED)'),
    ('WHITE', Color.WHITE, 'Белый (все LED)'),
]


# Уровни яркости
BRIGHTNESS_LEVELS = [
    ('Dim (0)', BRIGHTNESS_DIM, 0x7c),
    ('Normal (2)', BRIGHTNESS_NORMAL, 0x7e),
    ('Bright (3)', BRIGHTNESS_BRIGHT, 0x7f),
]


def test_color_brightness(device, color_name, color_idx, description):
    """Тест одного цвета с разными уровнями яркости"""
    print("\n" + "=" * 70)
    print(f"🎨 {color_name} (индекс {color_idx})")
    print(f"   {description}")
    print("=" * 70)
    print()

    for bright_name, bright_val, hex_val in BRIGHTNESS_LEVELS:
        print(f"   {bright_name:15} (0x{hex_val:02x} & 0b11 = {hex_val & 0b11}) ", end="", flush=True)
        device.set_all_pads(color_idx, bright_val)
        time.sleep(2.0)
        print("✓")

    # Clear
    device.clear()
    time.sleep(0.3)


def test_brightness_comparison(device):
    """Показать все 3 яркости одновременно на разных пэдах"""
    print("\n" + "=" * 70)
    print("🔆 СРАВНЕНИЕ ЯРКОСТИ (на одном экране)")
    print("=" * 70)
    print()
    print("Раскладка пэдов:")
    print()
    print("  12  13  14  15")
    print("   8   9  10  11")
    print("   4   5   6   7")
    print("   0   1   2   3")
    print()

    for color_name, color_idx, description in TEST_COLORS:
        print(f"\n{color_name}: {description}")
        print("  Левая колонка (0,4,8,12) = Dim")
        print("  Средние колонки (1,5,9,13 и 2,6,10,14) = Normal")
        print("  Правая колонка (3,7,11,15) = Bright")
        print()
        input("  Нажмите Enter для отображения...")

        # Set different brightness for different columns
        for pad_idx in range(16):
            column = pad_idx % 4
            if column == 0:
                # Leftmost column - Dim
                device.set_pad_light(pad_idx, color_idx, brightness=BRIGHTNESS_DIM, on=True)
            elif column == 3:
                # Rightmost column - Bright
                device.set_pad_light(pad_idx, color_idx, brightness=BRIGHTNESS_BRIGHT, on=True)
            else:
                # Middle columns - Normal
                device.set_pad_light(pad_idx, color_idx, brightness=BRIGHTNESS_NORMAL, on=True)

        input("  Сравните яркость. Enter для следующего цвета...")
        device.clear()
        time.sleep(0.3)


def main():
    print("=" * 70)
    print("🔆 Maschine MK3 - Brightness Test")
    print("=" * 70)
    print()

    # Find device
    devices = find_devices(max_count=1)

    if not devices:
        print("❌ Устройство не найдено")
        print("\nПроверьте:")
        print("  1. Подключен ли Maschine Mikro MK3")
        print("  2. Выполните: killall NIHardwareAgent")
        return

    device = devices[0]
    print(f"✅ Подключено: {device.serial}")
    print()

    print("=" * 70)
    print("ИНФОРМАЦИЯ О BRIGHTNESS")
    print("=" * 70)
    print()
    print("MK3 использует только 2 бита для яркости:")
    print()
    print("  Значение  | Hex  | & 0b11 | Уровень")
    print("  ----------|------|--------|----------")
    print("  Dim       | 0x7c | 0      | Тусклый")
    print("  Normal    | 0x7e | 2      | Средний")
    print("  Bright    | 0x7f | 3      | Максимум ⭐")
    print()
    print("Формула LED: (color << 2) | (brightness & 0b11)")
    print()

    print("=" * 70)
    print("РЕЖИМЫ ТЕСТА")
    print("=" * 70)
    print("  1. Последовательный тест (все пэды меняют яркость)")
    print("  2. Сравнение на одном экране (колонки = разная яркость)")
    print("  3. Оба режима")
    print("=" * 70)
    print()

    mode = input("Выберите режим (1/2/3) или Enter для режима 3: ").strip()
    if not mode:
        mode = "3"

    print()
    print("Нажмите Ctrl+C для остановки")

    try:
        if mode in ["1", "3"]:
            # Sequential test
            print("\n" + "=" * 70)
            print("РЕЖИМ 1: ПОСЛЕДОВАТЕЛЬНЫЙ ТЕСТ")
            print("=" * 70)

            for color_name, color_idx, description in TEST_COLORS:
                test_color_brightness(device, color_name, color_idx, description)

        if mode in ["2", "3"]:
            # Comparison test
            test_brightness_comparison(device)

        print("\n" + "=" * 70)
        print("✅ ТЕСТ ЗАВЕРШЁН")
        print("=" * 70)
        print()
        print("ВЫВОДЫ:")
        print("  • Brightness имеет только 3 реальных уровня (0, 2, 3)")
        print("  • Bright (3) - это максимум, больше нельзя!")
        print("  • Разные цвета визуально разной яркости:")
        print("    - RED (1 LED) - тусклее")
        print("    - ORANGE/MAGENTA (2 LED) - ярче")
        print("    - WHITE (3 LED) - самый яркий")
        print()

    except KeyboardInterrupt:
        print("\n\n🛑 Тест остановлен")

    finally:
        print("\nОчистка...")
        device.clear()
        device.close()
        print("✅ Устройство закрыто\n")


if __name__ == "__main__":
    main()

