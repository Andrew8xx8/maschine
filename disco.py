#!/usr/bin/env python3
"""
Maschine Mikro MK3 Disco Mode
==============================

Динамичные быстрые эффекты на 4 контроллерах.
Случайная смена эффектов, яркие цвета, высокая энергия!

Использует модуль maschine для управления устройствами.
"""

import time
import random
import math
from maschine import setup_devices_with_config, Color

# Яркие цвета для дискотеки
DISCO_COLORS = [
    Color.RED,
    Color.ORANGE,
    Color.YELLOW,
    Color.GREEN,
    Color.CYAN,
    Color.BLUE,
    Color.VIOLET,
    Color.MAGENTA,
    Color.FUCHSIA,
    Color.WHITE,
]

# Скорость эффектов (секунды)
EFFECT_DURATION = 3.0
FRAME_DELAY = 0.04  # 25 FPS


# ============================================================================
# ЭФФЕКТЫ
# ============================================================================

def fx_strobe(devices, duration):
    """Строб - быстрые вспышки"""
    start_time = time.time()
    pattern = [1] * 16

    while time.time() - start_time < duration:
        color = random.choice(DISCO_COLORS)

        for dev in devices:
            dev.set_pattern(pattern, color)
        time.sleep(0.05)

        for dev in devices:
            dev.clear()
        time.sleep(0.05)


def fx_random_pixels(devices, duration):
    """Случайные пиксели мигают"""
    start_time = time.time()

    while time.time() - start_time < duration:
        patterns = [[0]*16 for _ in range(4)]
        color = random.choice(DISCO_COLORS)

        # Случайно зажигаем 20-30 пикселей из 64
        for _ in range(random.randint(20, 30)):
            dev_idx = random.randint(0, 3)
            pad_idx = random.randint(0, 15)
            patterns[dev_idx][pad_idx] = 1

        for dev_idx, dev in enumerate(devices):
            dev.set_pattern(patterns[dev_idx], color)

        time.sleep(FRAME_DELAY)


def fx_chase(devices, duration):
    """Бегущие огни по всем устройствам"""
    start_time = time.time()
    frame = 0

    while time.time() - start_time < duration:
        patterns = [[0]*16 for _ in range(4)]
        color = random.choice(DISCO_COLORS)

        # Бегущая полоса шириной 8 пикселей
        for col in range(16):
            global_col = (col + frame) % 16
            dev_idx = global_col // 4
            local_col = global_col % 4

            for row in range(4):
                pad_idx = row * 4 + local_col
                patterns[dev_idx][pad_idx] = 1

        for dev_idx, dev in enumerate(devices):
            dev.set_pattern(patterns[dev_idx], color)

        frame += 1
        time.sleep(FRAME_DELAY)


def fx_diagonal_wave(devices, duration):
    """Диагональные волны"""
    start_time = time.time()
    frame = 0

    while time.time() - start_time < duration:
        patterns = [[0]*16 for _ in range(4)]
        color = random.choice(DISCO_COLORS)

        for dev_idx in range(4):
            for pad_idx in range(16):
                row = pad_idx // 4
                col = pad_idx % 4
                global_col = dev_idx * 4 + col

                # Диагональная волна
                if (global_col + row + frame) % 6 < 2:
                    patterns[dev_idx][pad_idx] = 1

        for dev_idx, dev in enumerate(devices):
            dev.set_pattern(patterns[dev_idx], color)

        frame += 1
        time.sleep(FRAME_DELAY)


def fx_explosion(devices, duration):
    """Взрывы от центра"""
    start_time = time.time()
    frame = 0
    center_x, center_y = 7.5, 1.5

    while time.time() - start_time < duration:
        patterns = [[0]*16 for _ in range(4)]
        color = random.choice(DISCO_COLORS)

        radius = (frame % 20) * 0.8

        for dev_idx in range(4):
            for pad_idx in range(16):
                row = pad_idx // 4
                col = pad_idx % 4
                global_col = dev_idx * 4 + col

                dist = math.sqrt((global_col - center_x)**2 + (row - center_y)**2)

                if abs(dist - radius) < 1.5:
                    patterns[dev_idx][pad_idx] = 1

        for dev_idx, dev in enumerate(devices):
            dev.set_pattern(patterns[dev_idx], color)

        frame += 1
        time.sleep(FRAME_DELAY)


def fx_matrix(devices, duration):
    """Матрица - падающие линии"""
    start_time = time.time()

    # Позиции капель для каждой колонки
    drops = [random.randint(-5, 3) for _ in range(16)]

    while time.time() - start_time < duration:
        patterns = [[0]*16 for _ in range(4)]
        color = random.choice(DISCO_COLORS)

        for col_global in range(16):
            row = drops[col_global]

            if 0 <= row < 4:
                dev_idx = col_global // 4
                col_local = col_global % 4
                pad_idx = row * 4 + col_local
                patterns[dev_idx][pad_idx] = 1

            # Двигаем вниз
            drops[col_global] += 1
            if drops[col_global] > 5:
                drops[col_global] = random.randint(-3, 0)

        for dev_idx, dev in enumerate(devices):
            dev.set_pattern(patterns[dev_idx], color)

        time.sleep(FRAME_DELAY * 1.5)


def fx_pulse(devices, duration):
    """Пульсация - все мигают синхронно"""
    start_time = time.time()
    frame = 0

    while time.time() - start_time < duration:
        intensity = (math.sin(frame * 0.3) + 1) / 2

        if intensity > 0.3:
            pattern = [1] * 16
            color = random.choice(DISCO_COLORS)
            for dev in devices:
                dev.set_pattern(pattern, color)
        else:
            for dev in devices:
                dev.clear()

        frame += 1
        time.sleep(FRAME_DELAY)


def fx_checkerboard(devices, duration):
    """Шахматная доска с инверсией"""
    start_time = time.time()
    frame = 0

    while time.time() - start_time < duration:
        patterns = [[0]*16 for _ in range(4)]
        color = random.choice(DISCO_COLORS)

        for dev_idx in range(4):
            for pad_idx in range(16):
                row = pad_idx // 4
                col = pad_idx % 4
                global_col = dev_idx * 4 + col

                # Шахматная доска с инверсией каждые 10 кадров
                if ((global_col + row + (frame // 10)) % 2) == 0:
                    patterns[dev_idx][pad_idx] = 1

        for dev_idx, dev in enumerate(devices):
            dev.set_pattern(patterns[dev_idx], color)

        frame += 1
        time.sleep(FRAME_DELAY)


def fx_snake(devices, duration):
    """Змейка бегает по дисплею"""
    start_time = time.time()

    # Позиции змейки (список координат)
    snake = [(7, 2), (6, 2), (5, 2), (4, 2)]  # Начальная змейка
    direction = 1  # 1 = вправо, -1 = влево

    while time.time() - start_time < duration:
        patterns = [[0]*16 for _ in range(4)]
        color = random.choice(DISCO_COLORS)

        # Двигаем голову
        head_col, head_row = snake[0]
        new_col = head_col + direction

        # Поворачиваем если дошли до края
        if new_col >= 16 or new_col < 0:
            direction *= -1
            head_row = (head_row + 1) % 4
            new_col = head_col + direction

        snake.insert(0, (new_col, head_row))
        snake = snake[:12]  # Длина змейки

        # Рисуем змейку
        for col, row in snake:
            if 0 <= col < 16 and 0 <= row < 4:
                dev_idx = col // 4
                col_local = col % 4
                pad_idx = row * 4 + col_local
                patterns[dev_idx][pad_idx] = 1

        for dev_idx, dev in enumerate(devices):
            dev.set_pattern(patterns[dev_idx], color)

        time.sleep(FRAME_DELAY * 2)


def fx_scanner(devices, duration):
    """Сканер Kitt (туда-сюда)"""
    start_time = time.time()
    frame = 0

    while time.time() - start_time < duration:
        patterns = [[0]*16 for _ in range(4)]
        color = random.choice(DISCO_COLORS)

        # Позиция сканера (0-15 и обратно)
        cycle_len = 30
        pos = frame % cycle_len
        if pos >= 15:
            pos = cycle_len - pos

        # Сканер с хвостом
        for offset in range(4):
            col = pos - offset
            if 0 <= col < 16:
                dev_idx = col // 4
                col_local = col % 4
                for row in range(4):
                    pad_idx = row * 4 + col_local
                    patterns[dev_idx][pad_idx] = 1

        for dev_idx, dev in enumerate(devices):
            dev.set_pattern(patterns[dev_idx], color)

        frame += 1
        time.sleep(FRAME_DELAY)


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 70)
    print("🎉 DISCO MODE - Maschine Mikro MK3")
    print("=" * 70)
    print()

    # Setup devices with configuration
    sorted_devices = setup_devices_with_config(max_count=4, show_numbers=True, show_duration=0.8)

    if len(sorted_devices) != 4:
        print(f"\n❌ Требуется 4 устройства, найдено: {len(sorted_devices)}")
        print("\n1. Подключите 4 контроллера Maschine Mikro MK3")
        print("2. Запустите: python3 device_setup.py")
        print("3. killall NIHardwareAgent (если нужно)")
        for device, _ in sorted_devices:
            device.close()
        return

    # Extract devices in correct order
    devices = [device for device, _ in sorted_devices]

    print("\n✅ Все устройства готовы!")
    print()
    print("=" * 70)
    print("🕺 ДИСКОТЕКА НАЧИНАЕТСЯ!")
    print("=" * 70)
    print()
    print("Быстрая смена эффектов, яркие цвета, высокая энергия!")
    print("Нажмите Ctrl+C для остановки")
    print()
    input("Press Enter to start the party... 🎊")
    print()

    # Список всех эффектов
    effects = [
        ("💥 СТРОБ", fx_strobe),
        ("✨ СЛУЧАЙНЫЕ ПИКСЕЛИ", fx_random_pixels),
        ("➡️  БЕГУЩИЕ ОГНИ", fx_chase),
        ("〰️  ДИАГОНАЛЬНЫЕ ВОЛНЫ", fx_diagonal_wave),
        ("💣 ВЗРЫВЫ", fx_explosion),
        ("📉 МАТРИЦА", fx_matrix),
        ("💓 ПУЛЬСАЦИЯ", fx_pulse),
        ("◼️  ШАХМАТНАЯ ДОСКА", fx_checkerboard),
        ("🐍 ЗМЕЙКА", fx_snake),
        ("↔️  СКАНЕР", fx_scanner),
    ]

    try:
        cycle = 0

        while True:
            cycle += 1

            # Случайный эффект
            effect_name, effect_func = random.choice(effects)

            print(f"[Цикл {cycle}] {effect_name}")
            effect_func(devices, EFFECT_DURATION)

    except KeyboardInterrupt:
        print("\n\n🛑 Вечеринка окончена!")

    finally:
        print("\nОчистка...")
        for dev in devices:
            dev.close()
        print("✓ Готово\n")


if __name__ == "__main__":
    main()

