#!/usr/bin/env python3
"""
Maschine Logo on Screen
=======================

Рисует логотип MASCHINE - руки, бьющие по падам.
"""

import time
import sys

sys.path.insert(0, '.')

from maschine import find_devices, Screen


def draw_maschine_logo(screen: Screen):
    """Нарисовать логотип MASCHINE - точная копия оригинала"""
    screen.clear()

    # === ПАДЫ ВНИЗУ (4 квадрата в ряд) ===
    pad_width = 14
    pad_height = 4
    pad_spacing = 10
    pad_y = 26
    start_x = 22

    for i in range(4):
        x = start_x + i * (pad_width + pad_spacing)
        # Трапеция с перспективой
        screen.draw_line(x + 2, pad_y, x + pad_width - 2, pad_y, on=True)  # Верх
        screen.draw_line(x, pad_y + pad_height, x + pad_width, pad_y + pad_height, on=True)  # Низ
        screen.draw_line(x + 2, pad_y, x, pad_y + pad_height, on=True)  # Левая
        screen.draw_line(x + pad_width - 2, pad_y, x + pad_width, pad_y + pad_height, on=True)  # Правая

        # Заливка
        screen.draw_line(x + 1, pad_y + 1, x + pad_width - 1, pad_y + 1, on=True)
        screen.draw_line(x + 1, pad_y + 2, x + pad_width - 1, pad_y + 2, on=True)
        screen.draw_line(x, pad_y + 3, x + pad_width, pad_y + 3, on=True)

    # === ЛЕВАЯ РУКА ===
    # Основной кулак (многоугольник)
    # Верхняя часть
    screen.draw_line(8, 8, 18, 4, on=True)  # Верхняя грань
    screen.draw_line(18, 4, 28, 4, on=True)  # Верх ровный
    screen.draw_line(28, 4, 35, 8, on=True)  # Правая верхняя грань

    # Правая сторона
    screen.draw_line(35, 8, 37, 12, on=True)
    screen.draw_line(37, 12, 35, 16, on=True)

    # Нижняя часть
    screen.draw_line(35, 16, 28, 19, on=True)
    screen.draw_line(28, 19, 18, 19, on=True)
    screen.draw_line(18, 19, 8, 16, on=True)

    # Левая сторона
    screen.draw_line(8, 16, 6, 12, on=True)
    screen.draw_line(6, 12, 8, 8, on=True)

    # Заливка левой руки
    for y in range(5, 19):
        if y < 8:
            left = 8 + (8 - y) * 2
            right = 28 - (8 - y) * 2
        elif y < 12:
            left = 7
            right = 36
        elif y < 16:
            left = 7
            right = 35
        else:
            left = 8 + (y - 16) * 2
            right = 35 - (y - 16) * 2
        screen.draw_line(left, y, right, y, on=True)

    # Складки/детали на левой руке
    screen.draw_line(12, 7, 14, 10, on=True)
    screen.draw_line(18, 6, 20, 9, on=True)
    screen.draw_line(24, 7, 26, 10, on=True)

    # === ПРАВАЯ РУКА ===
    # Основной кулак (зеркальное отражение)
    # Верхняя часть
    screen.draw_line(120, 8, 110, 4, on=True)
    screen.draw_line(110, 4, 100, 4, on=True)
    screen.draw_line(100, 4, 93, 8, on=True)

    # Левая сторона
    screen.draw_line(93, 8, 91, 12, on=True)
    screen.draw_line(91, 12, 93, 16, on=True)

    # Нижняя часть
    screen.draw_line(93, 16, 100, 19, on=True)
    screen.draw_line(100, 19, 110, 19, on=True)
    screen.draw_line(110, 19, 120, 16, on=True)

    # Правая сторона
    screen.draw_line(120, 16, 122, 12, on=True)
    screen.draw_line(122, 12, 120, 8, on=True)

    # Заливка правой руки
    for y in range(5, 19):
        if y < 8:
            left = 100 + (8 - y) * 2
            right = 110 - (8 - y) * 2
        elif y < 12:
            left = 92
            right = 121
        elif y < 16:
            left = 93
            right = 121
        else:
            left = 93 + (y - 16) * 2
            right = 120 - (y - 16) * 2
        screen.draw_line(left, y, right, y, on=True)

    # Складки/детали на правой руке
    screen.draw_line(116, 7, 114, 10, on=True)
    screen.draw_line(110, 6, 108, 9, on=True)
    screen.draw_line(104, 7, 102, 10, on=True)

    # === ЛИНИИ УДАРА И ЭФФЕКТЫ ===
    # От левой руки
    screen.draw_line(28, 19, 36, 26, on=True)
    screen.draw_line(30, 19, 46, 26, on=True)
    screen.draw_line(32, 19, 58, 26, on=True)

    # От правой руки
    screen.draw_line(100, 19, 92, 26, on=True)
    screen.draw_line(98, 19, 82, 26, on=True)
    screen.draw_line(96, 19, 70, 26, on=True)

    # Эффект удара - короткие линии
    # Под левой рукой
    screen.draw_line(20, 20, 18, 23, on=True)
    screen.draw_line(25, 20, 23, 23, on=True)
    screen.draw_line(30, 20, 32, 23, on=True)
    screen.draw_line(35, 20, 37, 23, on=True)

    # Под правой рукой
    screen.draw_line(108, 20, 110, 23, on=True)
    screen.draw_line(103, 20, 105, 23, on=True)
    screen.draw_line(98, 20, 96, 23, on=True)
    screen.draw_line(93, 20, 91, 23, on=True)


def draw_maschine_logo_v2(screen: Screen):
    """Альтернативная версия логотипа - более стилизованная"""
    screen.clear()

    # Рамка
    screen.draw_rect(0, 0, 128, 32, filled=False, on=True)

    # === ПАДЫ (более крупные, перспектива) ===
    pads = [
        (10, 22, 20, 6),   # Левый край
        (35, 22, 22, 7),   # Левый центр
        (62, 22, 22, 7),   # Правый центр
        (89, 22, 20, 6),   # Правый край
    ]

    for px, py, pw, ph in pads:
        # Трапеция с перспективой
        screen.draw_line(px + 2, py, px + pw - 2, py, on=True)  # Верх
        screen.draw_line(px, py + ph, px + pw, py + ph, on=True)  # Низ
        screen.draw_line(px + 2, py, px, py + ph, on=True)  # Левая
        screen.draw_line(px + pw - 2, py, px + pw, py + ph, on=True)  # Правая

        # Заливка
        for i in range(1, ph):
            left = px + 2 - int(i * 2 / ph)
            right = px + pw - 2 + int(i * 2 / ph)
            screen.draw_line(left, py + i, right, py + i, on=True)

    # === ЛЕВАЯ РУКА (угловатая, мощная) ===
    # Кулак
    fist_left = [
        (20, 5), (30, 5), (32, 7), (32, 12), (28, 14), (18, 14), (16, 12), (16, 7)
    ]
    for i in range(len(fist_left)):
        x1, y1 = fist_left[i]
        x2, y2 = fist_left[(i + 1) % len(fist_left)]
        screen.draw_line(x1, y1, x2, y2, on=True)

    # Заливка кулака
    for y in range(6, 13):
        screen.draw_line(17, y, 31, y, on=True)

    # Пальцы сверху
    screen.draw_rect(19, 2, 3, 3, filled=True, on=True)
    screen.draw_rect(23, 1, 3, 4, filled=True, on=True)
    screen.draw_rect(27, 2, 3, 3, filled=True, on=True)

    # === ПРАВАЯ РУКА ===
    # Кулак
    fist_right = [
        (98, 5), (108, 5), (110, 7), (110, 12), (106, 14), (96, 14), (94, 12), (94, 7)
    ]
    for i in range(len(fist_right)):
        x1, y1 = fist_right[i]
        x2, y2 = fist_right[(i + 1) % len(fist_right)]
        screen.draw_line(x1, y1, x2, y2, on=True)

    # Заливка кулака
    for y in range(6, 13):
        screen.draw_line(95, y, 109, y, on=True)

    # Пальцы сверху
    screen.draw_rect(97, 2, 3, 3, filled=True, on=True)
    screen.draw_rect(101, 1, 3, 4, filled=True, on=True)
    screen.draw_rect(105, 2, 3, 3, filled=True, on=True)

    # === ЛИНИИ УДАРА (энергичные) ===
    # От левой руки
    screen.draw_line(24, 14, 20, 22, on=True)
    screen.draw_line(26, 14, 32, 22, on=True)
    screen.draw_line(28, 14, 44, 22, on=True)

    # От правой руки
    screen.draw_line(102, 14, 106, 22, on=True)
    screen.draw_line(100, 14, 94, 22, on=True)
    screen.draw_line(98, 14, 82, 22, on=True)

    # Дополнительные линии (эффект движения)
    for i in range(3):
        offset = i * 2
        screen.draw_line(22 - offset, 15, 24 - offset, 18, on=True)
        screen.draw_line(104 + offset, 15, 102 + offset, 18, on=True)


def draw_maschine_logo_simple(screen: Screen):
    """Упрощенная версия - четкий и читаемый"""
    screen.clear()

    # === ПАДЫ (4 квадрата в ряд) ===
    pad_size = 16
    pad_y = 20
    pad_spacing = 8
    start_x = 16

    for i in range(4):
        x = start_x + i * (pad_size + pad_spacing)
        screen.draw_rect(x, pad_y, pad_size, 10, filled=True, on=True)

    # === РУКИ (стилизованные кулаки) ===

    # Левая рука
    # Кулак (прямоугольник + детали)
    screen.draw_rect(22, 4, 14, 10, filled=True, on=True)
    # Пальцы (небольшие квадратики сверху)
    screen.draw_rect(23, 2, 3, 2, filled=True, on=True)
    screen.draw_rect(27, 1, 3, 3, filled=True, on=True)
    screen.draw_rect(31, 2, 3, 2, filled=True, on=True)

    # Правая рука
    screen.draw_rect(92, 4, 14, 10, filled=True, on=True)
    screen.draw_rect(93, 2, 3, 2, filled=True, on=True)
    screen.draw_rect(97, 1, 3, 3, filled=True, on=True)
    screen.draw_rect(101, 2, 3, 2, filled=True, on=True)

    # === ЛИНИИ УДАРА ===
    # От левого кулака к падам
    screen.draw_line(29, 14, 24, 20, on=True)
    screen.draw_line(31, 14, 40, 20, on=True)
    screen.draw_line(33, 14, 56, 20, on=True)

    # От правого кулака к падам
    screen.draw_line(99, 14, 104, 20, on=True)
    screen.draw_line(97, 14, 88, 20, on=True)
    screen.draw_line(95, 14, 72, 20, on=True)

    # Короткие линии для эффекта удара (взрыв)
    for i in range(3):
        screen.draw_line(27 + i * 2, 15, 25 + i * 2, 18, on=True)
        screen.draw_line(101 - i * 2, 15, 103 - i * 2, 18, on=True)


def animate_logo(device, duration=5):
    """Анимация логотипа с разными вариантами"""
    screen = Screen()

    print("\n🎨 Анимация MASCHINE Logo")
    print("="*70)

    variants = [
        ("Версия 1 - Классическая", draw_maschine_logo),
        ("Версия 2 - Детальная", draw_maschine_logo_v2),
        ("Версия 3 - Простая", draw_maschine_logo_simple),
    ]

    start_time = time.time()
    idx = 0

    while time.time() - start_time < duration:
        name, draw_func = variants[idx % len(variants)]
        print(f"  → {name}")

        draw_func(screen)
        screen.write(device.device)

        time.sleep(2)
        idx += 1

    print("\n✅ Анимация завершена")


def main():
    """Главная функция"""
    print("🎨 MASCHINE Logo Screen")
    print("="*70)

    # Поиск устройства
    print("\n🔍 Поиск контроллера...")
    devices = find_devices(max_count=1)

    if not devices:
        print("❌ Контроллер не найден!")
        return

    device = devices[0]
    print(f"✅ Найден контроллер: {device.serial}")

    screen = Screen()

    try:
        while True:
            print("\n📋 Выберите вариант логотипа:")
            print("  1 - Классический")
            print("  2 - Детальный")
            print("  3 - Простой")
            print("  4 - Анимация всех вариантов (5 сек)")
            print("  0 - Очистить и выйти")
            print()

            choice = input("Выбор: ").strip()

            if choice == '1':
                print("\n🎨 Рисую классический логотип...")
                draw_maschine_logo(screen)
                screen.write(device.device)
                print("✅ Готово!")

            elif choice == '2':
                print("\n🎨 Рисую детальный логотип...")
                draw_maschine_logo_v2(screen)
                screen.write(device.device)
                print("✅ Готово!")

            elif choice == '3':
                print("\n🎨 Рисую простой логотип...")
                draw_maschine_logo_simple(screen)
                screen.write(device.device)
                print("✅ Готово!")

            elif choice == '4':
                animate_logo(device, duration=5)

            elif choice == '0':
                print("\n✅ Очистка экрана и выход...")
                screen.clear()
                screen.write(device.device)
                break
            else:
                print("❌ Неверный выбор!")

    except KeyboardInterrupt:
        print("\n\n⚠️  Прервано пользователем")
        screen.clear()
        screen.write(device.device)

    finally:
        print("\n👋 До свидания!")


if __name__ == '__main__':
    main()

