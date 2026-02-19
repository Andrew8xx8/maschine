#!/usr/bin/env python3
"""
Maschine Mikro MK3 - Pad Text Display
=====================================

Статичное отображение текста на 4 устройствах (16×4 сетка пэдов).

Usage:
    python pad_text_display.py                  # Default "HANDS ON"
    python pad_text_display.py "YOUR TEXT"      # Custom text
    python pad_text_display.py "HI" --color 9   # Custom color (0-17)
"""

import sys
import time
from pathlib import Path
from maschine import (
    find_devices,
    close_all_devices,
    Color,
    display_text_on_pads,
    get_text_width,
    setup_devices_with_config,
    display_logo_on_devices,
)

LOGO_PATH = Path(__file__).parent / "logo.png"


# Preset color cycle for rainbow effect
RAINBOW_COLORS = [
    Color.RED,
    Color.ORANGE,
    Color.YELLOW,
    Color.LIME,
    Color.GREEN,
    Color.CYAN,
    Color.BLUE,
    Color.PURPLE,
    Color.MAGENTA,
]


def main():
    # Parse arguments
    text = "HANDSON"
    color = Color.CYAN
    animate = False
    compact = False

    if len(sys.argv) > 1:
        if sys.argv[1] == "--help":
            print(__doc__)
            print("\nРежимы шрифтов:")
            print("  Стандартный (3x4): ~4 символа в 16px")
            print("  Компактный (2x4):  ~7 символов в 16px (--compact)")
            print("\nПримеры:")
            print("  python pad_text_display.py 'PLAY'              # 4 буквы стандартно")
            print("  python pad_text_display.py 'HANDSON' --compact # 7 букв компактно")
            print("  python pad_text_display.py 'HI' --rainbow      # радуга")
            return
        text = sys.argv[1]

    if "--color" in sys.argv:
        idx = sys.argv.index("--color")
        if idx + 1 < len(sys.argv):
            color = int(sys.argv[idx + 1])

    if "--rainbow" in sys.argv:
        animate = True

    if "--compact" in sys.argv:
        compact = True

    # Auto-detect compact mode if text is too wide
    width_standard = get_text_width(text, compact=False)
    width_compact = get_text_width(text, compact=True)

    if not compact and width_standard > 16 and width_compact <= 16:
        compact = True
        print(f"⚡ Авто: компактный шрифт ({width_standard}px → {width_compact}px)")

    width = get_text_width(text, compact=compact)
    font_type = 'компактный 2x4' if compact else 'стандартный 3x4'
    print(f"📝 Текст: '{text}' ({width}px, {font_type})")

    if width > 16:
        print(f"⚠️  Текст слишком широкий ({width}px > 16px), будет обрезан")
        if not compact:
            print("   Попробуйте --compact для более короткого шрифта")

    # Find and setup devices
    print("\n🔍 Поиск устройств...")
    sorted_devices = setup_devices_with_config(max_count=4)

    if len(sorted_devices) < 4:
        print(f"❌ Найдено {len(sorted_devices)} устройств, требуется 4")
        close_all_devices([d for d, _ in sorted_devices])
        return

    # Extract devices from tuples (device, device_num)
    devices = [d for d, _ in sorted_devices]
    print(f"✅ Подключено {len(devices)} устройств")

    # Display logo on screens (if logo exists)
    if LOGO_PATH.exists():
        display_logo_on_devices(devices, LOGO_PATH)

    try:
        if animate:
            print(f"\n🌈 Режим радуги - Ctrl+C для выхода")
            color_idx = 0
            while True:
                display_text_on_pads(devices, text, RAINBOW_COLORS[color_idx], compact=compact)
                color_idx = (color_idx + 1) % len(RAINBOW_COLORS)
                time.sleep(0.3)
        else:
            print(f"\n✨ Отображаю текст цветом {color}")
            display_text_on_pads(devices, text, color, compact=compact)

            print("\nНажмите Enter для выхода...")
            input()

    except KeyboardInterrupt:
        print("\n\n🛑 Остановлено")

    finally:
        print("Очистка...")
        for dev in devices:
            dev.clear()
        close_all_devices()
        print("✓ Готово")


if __name__ == "__main__":
    main()

