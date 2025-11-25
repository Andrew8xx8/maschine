#!/usr/bin/env python3
"""
Тест показа номеров устройств
==============================

Простой скрипт для проверки что устройства правильно идентифицируются.
"""

from maschine import setup_devices_with_config

def main():
    print("=" * 70)
    print("🔍 Тест идентификации устройств")
    print("=" * 70)
    print()

    # Setup devices with visual identification
    print("Инициализация устройств...")
    print("(каждое устройство покажет свой номер: 1, 2, 3 или 4 пэда)")
    print()

    sorted_devices = setup_devices_with_config(
        max_count=4,
        show_numbers=True,      # Показать номера визуально
        show_duration=1.5       # Длительность показа
    )

    if not sorted_devices:
        print("❌ Устройства не найдены!")
        return

    print("\n" + "=" * 70)
    print("✅ Подключенные устройства:")
    print("=" * 70)

    for device, device_num in sorted_devices:
        print(f"  Device {device_num} → Serial: {device.serial}")

    print()
    print("Нажмите Enter для выхода...")
    input()

    # Cleanup
    for device, _ in sorted_devices:
        device.close()

    print("✅ Готово!")


if __name__ == "__main__":
    main()

