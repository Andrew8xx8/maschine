#!/usr/bin/env python3
"""
🔧 Maschine MK3 Device Setup Utility
=====================================

Утилита для настройки постоянного порядка контроллеров.

Использование:
    python3 device_setup.py          # Настроить порядок устройств
    python3 device_setup.py --show   # Показать текущую конфигурацию

Конфигурация сохраняется в ~/.maschine_device_config.json
"""

import time
from maschine import (
    find_devices,
    Color,
    BRIGHTNESS_BRIGHT,
    load_device_config,
    save_device_config,
    get_config_path,
)


def show_config():
    """Показать текущую конфигурацию"""
    config = load_device_config()

    if not config:
        print("\n❌ Конфигурация не найдена")
        print(f"   Запустите: python3 device_setup.py")
        return

    print("\n" + "=" * 70)
    print("📋 Текущая конфигурация устройств")
    print("=" * 70)
    print()

    # Sort by device number
    sorted_items = sorted(config.items(), key=lambda x: x[1])

    for serial, device_num in sorted_items:
        print(f"  Device {device_num} → Serial: {serial}")

    print()
    print(f"📁 Файл конфигурации: {get_config_path()}")
    print()


def identify_device(device, num_pads, device_name):
    """
    Подсветить устройство для идентификации

    Args:
        device: MaschineDevice
        num_pads: Количество пэдов для подсветки (1-4)
        device_name: Название для отображения
    """
    print(f"\n{'='*70}")
    print(f"🔍 Устройство: {device_name}")
    print(f"   Serial: {device.serial}")
    print(f"   Подсвечиваю {num_pads} {'пэд' if num_pads == 1 else 'пэда' if num_pads < 5 else 'пэдов'}...")
    print("=" * 70)

    # Clear all first
    device.clear()
    time.sleep(0.2)

    # Light up specified number of pads in top-left corner
    # Pattern: 1 pad = top-left, 2 pads = top row, 3 pads = top + 1 mid, 4 pads = top + 2 mid
    pad_patterns = {
        1: [12],              # 1 пэд: верхний левый
        2: [12, 13],          # 2 пэда: верхний ряд слева
        3: [12, 13, 14],      # 3 пэда: верхний ряд
        4: [12, 13, 14, 15],  # 4 пэда: весь верхний ряд
    }

    pads_to_light = pad_patterns.get(num_pads, [12])

    # Blink pattern 3 times for visibility
    for _ in range(3):
        for pad in pads_to_light:
            device.set_pad_light(pad, Color.CYAN, brightness=BRIGHTNESS_BRIGHT, on=True)
        time.sleep(0.3)

        device.clear()
        time.sleep(0.2)

    # Keep lit while user inputs
    for pad in pads_to_light:
        device.set_pad_light(pad, Color.CYAN, brightness=BRIGHTNESS_BRIGHT, on=True)


def setup_devices():
    """Интерактивная настройка порядка устройств"""
    print("\n" + "=" * 70)
    print("🎹 Настройка порядка устройств Maschine Mikro MK3")
    print("=" * 70)
    print()
    print("Эта утилита поможет вам настроить постоянный порядок контроллеров.")
    print("Каждое устройство будет подсвечено уникальным паттерном:")
    print("  • 1 пэд   = первое найденное устройство")
    print("  • 2 пэда  = второе найденное устройство")
    print("  • 3 пэда  = третье найденное устройство")
    print("  • 4 пэда  = четвёртое найденное устройство")
    print()
    print("Вы укажете какой номер присвоить каждому контроллеру (1-4).")
    print("=" * 70)

    # Find devices
    print("\n🔍 Поиск контроллеров...")
    devices = find_devices(max_count=4)

    if not devices:
        print("❌ Устройства не найдены")
        print("\nTroubleshooting:")
        print("  1. Подключите Maschine Mikro MK3")
        print("  2. Убейте NIHardwareAgent:")
        print("     killall NIHardwareAgent")
        return None

    print(f"✅ Найдено устройств: {len(devices)}")
    print()

    # Setup mapping
    config = {}
    used_numbers = set()

    for i, device in enumerate(devices, 1):
        # Identify device with unique pattern
        identify_device(device, i, f"Устройство #{i}")

        while True:
            try:
                print()
                num_str = input(f"Какой номер присвоить этому контроллеру? (1-4): ").strip()

                if not num_str:
                    print("❌ Введите число!")
                    continue

                num = int(num_str)

                if num < 1 or num > 4:
                    print(f"❌ Номер должен быть от 1 до 4")
                    continue

                if num in used_numbers:
                    print(f"❌ Номер {num} уже используется!")
                    continue

                config[device.serial] = num
                used_numbers.add(num)
                print(f"✅ Serial {device.serial} → Device {num}")

                # Clear this device
                device.clear()
                break

            except ValueError:
                print("❌ Введите число!")
            except KeyboardInterrupt:
                print("\n\n🛑 Настройка отменена")
                # Clear all devices
                for dev in devices:
                    dev.clear()
                    dev.close()
                return None

    # Clear all devices
    for device in devices:
        device.clear()

    # Show summary
    print("\n" + "=" * 70)
    print("📋 Итоговая конфигурация:")
    print("=" * 70)

    sorted_config = sorted(config.items(), key=lambda x: x[1])
    for serial, num in sorted_config:
        print(f"  Device {num} → {serial}")

    print("\n💾 Сохранить эту конфигурацию? (y/n): ", end='')

    try:
        answer = input().strip().lower()
        if answer in ['y', 'yes', 'д', 'да', '']:
            if save_device_config(config):
                print(f"\n✅ Конфигурация сохранена: {get_config_path()}")
                print()
                print("Теперь все игры и программы будут использовать этот порядок:")
                print("  • midi_bridge.py")
                print("  • memory_match.py")
                print("  • pvp_whack.py")
                print("  • reaction_game.py")
                print("  • disco.py")
                print("  • и другие...")
                print()
                return config
        else:
            print("\n❌ Конфигурация не сохранена")
    except KeyboardInterrupt:
        print("\n\n🛑 Отменено")

    finally:
        # Close all devices
        for device in devices:
            device.close()

    return None


def main():
    import sys

    # Parse arguments
    if '--show' in sys.argv or '-s' in sys.argv:
        show_config()
        return

    # Run setup
    setup_devices()


if __name__ == "__main__":
    main()

