#!/usr/bin/env python3
"""
Image to Maschine Screens
=========================

Выводит изображение 128x32 на все подключенные контроллеры Maschine.
Поддерживает форматы: PNG, JPG, GIF, BMP
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, '.')

from maschine import find_devices, Screen

try:
    from PIL import Image
except ImportError:
    print("❌ Требуется библиотека Pillow!")
    print("   Установите: pip install Pillow")
    sys.exit(1)


def load_image_to_screen(image_path: str, threshold: int = 128) -> Screen:
    """
    Загрузить изображение и конвертировать в Screen

    Args:
        image_path: Путь к изображению
        threshold: Порог яркости для конвертации в ч/б (0-255)

    Returns:
        Screen объект с загруженным изображением
    """
    # Загрузить изображение
    img = Image.open(image_path)

    # Конвертировать в grayscale
    img = img.convert('L')

    # Изменить размер до 128x32
    img = img.resize((128, 32), Image.Resampling.LANCZOS)

    # Создать Screen
    screen = Screen()
    screen.clear()

    # Конвертировать пиксели
    pixels = img.load()
    for y in range(32):
        for x in range(128):
            # Если пиксель светлее порога - включить (инвертировано)
            if pixels[x, y] > threshold:
                screen.set_pixel(x, y, on=True)

    return screen


def display_image_on_all_devices(image_path: str, threshold: int = 128):
    """
    Отобразить изображение на всех подключенных устройствах

    Args:
        image_path: Путь к изображению
        threshold: Порог яркости (0-255)
    """
    print(f"\n🔍 Поиск контроллеров...")
    devices = find_devices(max_count=4)

    if not devices:
        print("❌ Контроллеры не найдены!")
        return

    print(f"✅ Найдено устройств: {len(devices)}")
    for i, device in enumerate(devices, 1):
        print(f"   {i}. {device.serial}")

    print(f"\n📷 Загрузка изображения: {image_path}")
    try:
        screen = load_image_to_screen(image_path, threshold)
    except FileNotFoundError:
        print(f"❌ Файл не найден: {image_path}")
        return
    except Exception as e:
        print(f"❌ Ошибка загрузки изображения: {e}")
        return

    print(f"✅ Изображение загружено и конвертировано")

    print(f"\n📤 Отправка на {len(devices)} устройств...")
    for i, device in enumerate(devices, 1):
        screen.write(device.device)
        print(f"   ✓ Устройство {i} ({device.serial})")

    print(f"\n🎉 Готово! Изображение отображается на всех устройствах.")


def interactive_mode():
    """Интерактивный режим с меню"""
    print("🖼️  Image to Maschine Screens")
    print("="*70)

    # Поиск устройств
    print(f"\n🔍 Поиск контроллеров...")
    devices = find_devices(max_count=4)

    if not devices:
        print("❌ Контроллеры не найдены!")
        return

    print(f"✅ Найдено устройств: {len(devices)}")
    for i, device in enumerate(devices, 1):
        print(f"   {i}. {device.serial}")

    threshold = 128

    while True:
        print("\n" + "="*70)
        print("📋 МЕНЮ")
        print("="*70)
        print(f"  Текущий порог яркости: {threshold}")
        print()
        print("  1 - Загрузить изображение")
        print("  2 - Изменить порог яркости")
        print("  3 - Очистить все экраны")
        print("  0 - Выход")
        print()

        choice = input("Выбор: ").strip()

        if choice == '1':
            print("\n📂 Введите путь к изображению:")
            print("   (поддерживаются: PNG, JPG, GIF, BMP)")
            image_path = input("Путь: ").strip()

            if not image_path:
                print("❌ Путь не указан!")
                continue

            # Убрать кавычки если есть
            image_path = image_path.strip('"').strip("'")

            if not os.path.exists(image_path):
                print(f"❌ Файл не найден: {image_path}")
                continue

            print(f"\n📷 Загрузка изображения...")
            try:
                screen = load_image_to_screen(image_path, threshold)
                print(f"✅ Изображение загружено")

                print(f"\n📤 Отправка на {len(devices)} устройств...")
                for i, device in enumerate(devices, 1):
                    screen.write(device.device)
                    print(f"   ✓ Устройство {i}")

                print(f"\n🎉 Готово!")

            except Exception as e:
                print(f"❌ Ошибка: {e}")

        elif choice == '2':
            print("\n⚙️  Порог яркости (0-255):")
            print("   Меньше значение = больше белого")
            print("   Больше значение = больше черного")
            print(f"   Текущее: {threshold}")
            print()
            new_threshold = input("Новое значение: ").strip()

            try:
                new_threshold = int(new_threshold)
                if 0 <= new_threshold <= 255:
                    threshold = new_threshold
                    print(f"✅ Порог установлен: {threshold}")
                else:
                    print("❌ Значение должно быть от 0 до 255")
            except ValueError:
                print("❌ Неверное значение")

        elif choice == '3':
            print("\n🧹 Очистка всех экранов...")
            screen = Screen()
            screen.clear()
            for i, device in enumerate(devices, 1):
                screen.write(device.device)
                print(f"   ✓ Устройство {i} очищено")
            print("✅ Все экраны очищены")

        elif choice == '0':
            print("\n🧹 Очистка экранов перед выходом...")
            screen = Screen()
            screen.clear()
            for device in devices:
                screen.write(device.device)
            print("\n👋 До свидания!")
            break

        else:
            print("❌ Неверный выбор!")


def main():
    """Главная функция"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Вывод изображений 128x32 на контроллеры Maschine',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:

  # Интерактивный режим
  python3 image_to_screen.py

  # Вывести изображение напрямую
  python3 image_to_screen.py logo.png

  # С настройкой порога яркости
  python3 image_to_screen.py logo.png --threshold 150

  # Поддерживаемые форматы: PNG, JPG, GIF, BMP
  # Изображения автоматически масштабируются до 128x32
        """
    )

    parser.add_argument(
        'image',
        nargs='?',
        help='Путь к изображению (необязательно для интерактивного режима)'
    )

    parser.add_argument(
        '-t', '--threshold',
        type=int,
        default=128,
        help='Порог яркости для конвертации в ч/б (0-255, по умолчанию: 128)'
    )

    args = parser.parse_args()

    if args.image:
        # Прямой режим - вывести изображение
        display_image_on_all_devices(args.image, args.threshold)
    else:
        # Интерактивный режим
        try:
            interactive_mode()
        except KeyboardInterrupt:
            print("\n\n⚠️  Прервано пользователем")
            print("🧹 Очистка экранов...")
            devices = find_devices(max_count=4)
            if devices:
                screen = Screen()
                screen.clear()
                for device in devices:
                    screen.write(device.device)
            print("👋 До свидания!")


if __name__ == '__main__':
    main()

