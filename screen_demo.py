#!/usr/bin/env python3
"""
Maschine Mikro MK3 Screen Demo
==============================

Демонстрация работы с экранами контроллера.
"""

import time
import sys
from datetime import datetime

# Добавляем путь к модулю maschine
sys.path.insert(0, '.')

from maschine import find_devices
from maschine.screen import Screen, create_demo_pattern, SCREEN_WIDTH, SCREEN_HEIGHT
from maschine.screen_font import draw_text_5x7, draw_time, draw_digit


def demo_patterns(device):
    """Демонстрация различных графических паттернов"""
    print("\n🖥️  ДЕМО ГРАФИЧЕСКИХ ПАТТЕРНОВ")
    print("="*70)

    screen = Screen()

    # 1. Паттерн из screen.py
    print("\n1️⃣  Демо-паттерн (рамка, линии, круги)...")
    create_demo_pattern(screen)
    screen.write(device.device)
    time.sleep(2)

    # 2. Шахматная доска
    print("2️⃣  Шахматная доска...")
    screen.clear()
    cell_size = 8
    for i in range(0, SCREEN_HEIGHT, cell_size):
        for j in range(0, SCREEN_WIDTH, cell_size):
            if ((i // cell_size) + (j // cell_size)) % 2 == 0:
                screen.draw_rect(j, i, cell_size, cell_size, filled=True, on=True)
    screen.write(device.device)
    time.sleep(2)

    # 3. Концентрические окружности
    print("3️⃣  Концентрические окружности...")
    screen.clear()
    for r in range(3, 16, 3):
        screen.draw_circle(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, r, filled=False, on=True)
    screen.write(device.device)
    time.sleep(2)

    # 4. Горизонтальные линии
    print("4️⃣  Горизонтальные линии...")
    screen.clear()
    for y in range(0, SCREEN_HEIGHT, 4):
        screen.draw_line(0, y, SCREEN_WIDTH - 1, y, on=True)
    screen.write(device.device)
    time.sleep(2)

    # 5. Вертикальные линии
    print("5️⃣  Вертикальные линии...")
    screen.clear()
    for x in range(0, SCREEN_WIDTH, 4):
        screen.draw_line(x, 0, x, SCREEN_HEIGHT - 1, on=True)
    screen.write(device.device)
    time.sleep(2)


def demo_text(device):
    """Демонстрация работы с текстом"""
    print("\n📝 ДЕМО ТЕКСТА")
    print("="*70)

    screen = Screen()

    # 1. Цифры разных размеров
    print("\n1️⃣  Цифры (разные масштабы)...")
    screen.clear()
    for i in range(10):
        draw_digit(screen, i * 12, 5, i, scale=1)
    screen.write(device.device)
    time.sleep(2)

    # 2. Большие цифры
    print("2️⃣  Большие цифры...")
    screen.clear()
    draw_digit(screen, 10, 8, 1, scale=2)
    draw_digit(screen, 40, 8, 2, scale=2)
    draw_digit(screen, 70, 8, 3, scale=2)
    screen.write(device.device)
    time.sleep(2)

    # 3. Текст
    print("3️⃣  Текст HELLO...")
    screen.clear()
    draw_text_5x7(screen, 10, 10, "HELLO", scale=2)
    screen.write(device.device)
    time.sleep(2)

    # 4. Разный текст
    print("4️⃣  MASCHINE MK3...")
    screen.clear()
    draw_text_5x7(screen, 5, 3, "MASCHINE", scale=1)
    draw_text_5x7(screen, 25, 13, "MK3", scale=2)
    screen.write(device.device)
    time.sleep(2)


def demo_clock(device, duration=10):
    """Демонстрация часов"""
    print(f"\n🕐 ДЕМО ЧАСОВ ({duration} секунд)")
    print("="*70)

    screen = Screen()

    start_time = time.time()
    while time.time() - start_time < duration:
        screen.clear()

        now = datetime.now()

        # Рамка
        screen.draw_rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, filled=False, on=True)

        # Время (большое)
        draw_time(screen, 5, 10, now.hour, now.minute, now.second, scale=1)

        screen.write(device.device)
        time.sleep(0.5)


def demo_animation(device):
    """Демонстрация анимации"""
    print("\n🎬 ДЕМО АНИМАЦИИ")
    print("="*70)

    screen = Screen()

    # 1. Двигающийся круг
    print("\n1️⃣  Двигающийся круг...")
    for x in range(10, SCREEN_WIDTH - 10, 3):
        screen.clear()
        screen.draw_circle(x, SCREEN_HEIGHT // 2, 8, filled=True, on=True)
        screen.write(device.device)
        time.sleep(0.03)

    # 2. Растущий круг
    print("2️⃣  Растущий круг...")
    for r in range(1, 16):
        screen.clear()
        screen.draw_circle(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, r, filled=False, on=True)
        screen.write(device.device)
        time.sleep(0.08)

    # 3. Вращающаяся линия
    print("3️⃣  Вращающаяся линия...")
    import math
    center_x = SCREEN_WIDTH // 2
    center_y = SCREEN_HEIGHT // 2
    radius = 15

    for angle in range(0, 360, 5):
        screen.clear()
        rad = math.radians(angle)
        x = int(center_x + radius * math.cos(rad))
        y = int(center_y + radius * math.sin(rad))
        screen.draw_line(center_x, center_y, x, y, on=True)
        screen.write(device.device)
        time.sleep(0.03)


def interactive_menu(device):
    """Интерактивное меню"""
    print("\n📋 ИНТЕРАКТИВНОЕ МЕНЮ")
    print("="*70)
    print("\nВыберите демо:")
    print("  1 - Графические паттерны")
    print("  2 - Текст и шрифты")
    print("  3 - Часы (10 сек)")
    print("  4 - Анимации")
    print("  5 - Все подряд")
    print("  0 - Очистить и выйти")
    print()


def main():
    """Главная функция"""
    print("🖥️  Maschine Mikro MK3 - Screen Demo")
    print("="*70)

    # Поиск устройства
    print("\n🔍 Поиск контроллера...")
    devices = find_devices(max_count=1)

    if not devices:
        print("❌ Контроллер не найден!")
        return

    device = devices[0]
    print(f"✅ Найден контроллер: {device.serial}")

    try:
        while True:
            interactive_menu(device)
            choice = input("Выбор: ").strip()

            if choice == '1':
                demo_patterns(device)
            elif choice == '2':
                demo_text(device)
            elif choice == '3':
                demo_clock(device, duration=10)
            elif choice == '4':
                demo_animation(device)
            elif choice == '5':
                print("\n🎪 ПОЛНОЕ ДЕМО")
                print("="*70)
                demo_patterns(device)
                demo_text(device)
                demo_clock(device, duration=5)
                demo_animation(device)
            elif choice == '0':
                print("\n✅ Очистка экрана и выход...")
                screen = Screen()
                screen.clear()
                screen.write(device.device)
                break
            else:
                print("❌ Неверный выбор!")

    except KeyboardInterrupt:
        print("\n\n⚠️  Прервано пользователем")
        screen = Screen()
        screen.clear()
        screen.write(device.device)

    finally:
        print("\n👋 До свидания!")


if __name__ == '__main__':
    main()

