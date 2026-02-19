#!/usr/bin/env python3
"""
🃏 MEMORY MATCH - Параллельная игра на память для 2 игроков
=========================================================

Player 1: Устройства 1-2 (32 пэда) - играет ОДНОВРЕМЕННО
Player 2: Устройства 3-4 (32 пэда) - играет ОДНОВРЕМЕННО

Правила:
- Каждый игрок играет на СВОИХ 2 устройствах параллельно (8×4 пэда)
- 16 пар (32 карты) для каждого игрока
- Цвета карт: Red, Yellow, Green, Violet, Blue (5 цветов)
- Показываются все карты на 6 секунд
- Открывай 2 карты подряд на своих устройствах
- Пара совпала → карты остаются гореть своими цветами, +1 очко
- Не совпала → показываются 0.5 сек, затем гаснут
- Кто быстрее найдёт все пары → ПОБЕДИЛ!
"""

import time
import random

from maschine import (
    setup_devices_with_config,
    Color,
    BRIGHTNESS_BRIGHT,
    PadEventType,
)

# Контрастные цвета из правильной палитры MK3 (16 пар = 32 карты на игрока!)
# Используем только 5 хорошо различимых цветов
CARD_COLORS = [
    Color.RED,      # Red (красный)
    Color.YELLOW,   # Yellow (жёлтый)
    Color.GREEN,    # Green (зелёный)
    Color.VIOLET,   # Violet (фиолетовый)
    Color.BLUE,     # Blue (синий)
    Color.RED,      # Red (повтор)
    Color.YELLOW,   # Yellow (повтор)
    Color.GREEN,    # Green (повтор)
    Color.VIOLET,   # Violet (повтор)
    Color.BLUE,     # Blue (повтор)
    Color.RED,      # Red (еще раз)
    Color.YELLOW,   # Yellow (еще раз)
    Color.GREEN,    # Green (еще раз)
    Color.VIOLET,   # Violet (еще раз)
    Color.BLUE,     # Blue (еще раз)
    Color.RED,      # Red (четвертый раз)
]

# Game settings
REVEAL_TIME = 6.0  # Увеличено в 2 раза для запоминания
MISMATCH_SHOW_TIME = 0.5  # Показываем неверные очень коротко


def decode_pad_events(data):
    """Decode pad events - returns list of pressed pad indices"""
    if not data or data[0] != 0x02:
        return []

    pressed = []
    for i in range(1, len(data), 3):
        if i + 2 >= len(data):
            break

        pad_idx = data[i]
        event_byte = data[i + 1]
        vel_low = data[i + 2]

        if i > 1 and pad_idx == 0 and event_byte == 0 and vel_low == 0:
            break

        event_type = event_byte & 0xf0

        if event_type == PadEventType.NOTE_ON:
            if 0 <= pad_idx <= 15:
                pressed.append(pad_idx)

    return pressed


class PlayerState:
    """Стейт одного игрока"""
    def __init__(self, player_id, device_indices):
        self.player_id = player_id  # 1 или 2
        self.device_indices = device_indices  # [0, 1] или [2, 3]

        # Создаём 32 карты (16 пар) для этого игрока
        cards = []
        for color in CARD_COLORS:
            cards.append(color)
            cards.append(color)
        random.shuffle(cards)

        # Распределяем по 32 пэдам игрока (2 устройства × 16 пэдов)
        self.board = {}  # {(local_dev, pad): color}
        card_idx = 0
        for local_dev in range(2):  # 2 устройства на игрока
            for pad_idx in range(16):
                self.board[(local_dev, pad_idx)] = cards[card_idx]
                card_idx += 1

        self.matched = set()  # {(local_dev, pad), ...}
        self.selected = []    # [(local_dev, pad), ...]
        self.mismatch_hide_time = 0
        self.score = 0
        self.finished = False
        self.finish_time = None

    def get_global_device_index(self, local_dev):
        """Конвертируем локальный индекс (0-1) в глобальный (0-3)"""
        return self.device_indices[local_dev]


# Device ordering removed - now using saved configuration from device_setup.py


def show_countdown(devices):
    """Countdown"""
    for count in [3, 2, 1]:
        print(f"  {count}...")
        for dev in devices:
            for pad in range(16):
                dev.set_pad_light(pad, 7, on=True)
  # Один HID write для всех 16 пэдов
        time.sleep(0.3)
        for dev in devices:
            dev.clear()
        time.sleep(0.7)
    print("  GO!")


def play_round(devices):
    """Play one round - параллельно!"""
    print("\n" + "=" * 70)
    print("🎮 НОВЫЙ РАУНД - ПАРАЛЛЕЛЬНАЯ ИГРА!")
    print("=" * 70)

    # Создаём стейт для каждого игрока
    p1 = PlayerState(1, [0, 1])  # Устройства 0-1
    p2 = PlayerState(2, [2, 3])  # Устройства 2-3

    # ========================================
    # ФАЗА 1: Показываем все карты
    # ========================================
    print("\n🃏 Запоминайте карты!")

    # Player 1
    for (local_dev, pad_idx), color in p1.board.items():
        global_dev = p1.get_global_device_index(local_dev)
        devices[global_dev].set_pad_light(pad_idx, color, on=True)

    # Player 2
    for (local_dev, pad_idx), color in p2.board.items():
        global_dev = p2.get_global_device_index(local_dev)
        devices[global_dev].set_pad_light(pad_idx, color, on=True)

    time.sleep(REVEAL_TIME)

    # ========================================
    # ФАЗА 2: Скрываем
    # ========================================
    print("🔒 Карты скрыты!")
    for dev in devices:
        dev.clear()
    time.sleep(0.5)

    print("\n⚔️  НАЧАЛИ! Оба игрока играют ОДНОВРЕМЕННО!")
    print()

    # ========================================
    # ФАЗА 3: Параллельный игровой цикл
    # ========================================
    while True:
        current_time = time.time()

        # Проверяем конец игры
        if p1.finished and p2.finished:
            # Определяем победителя
            if p1.finish_time < p2.finish_time:
                winner = 1
            elif p2.finish_time < p1.finish_time:
                winner = 2
            else:
                winner = 0  # Ничья (невозможно, но на всякий случай)

            # Анимация финиша
            print("\n🎉 ФИНИШ! Показываем результат...")

            # Моргаем 5 раз
            for _ in range(5):
                # Победитель = зелёный, проигравший = красный
                for local_dev in range(2):
                    # Player 1
                    p1_global = p1.get_global_device_index(local_dev)
                    color_p1 = 7 if winner == 1 else 1  # Green or Red
                    for pad_idx in range(16):
                        devices[p1_global].set_pad_light(pad_idx, color_p1, on=True)

                    # Player 2
                    p2_global = p2.get_global_device_index(local_dev)
                    color_p2 = 7 if winner == 2 else 1  # Green or Red
                    for pad_idx in range(16):
                        devices[p2_global].set_pad_light(pad_idx, color_p2, on=True)

                time.sleep(0.3)

                # Гасим
                for dev in devices:
                    dev.clear()
                time.sleep(0.3)

            # Последний раз зажигаем
            for local_dev in range(2):
                p1_global = p1.get_global_device_index(local_dev)
                color_p1 = 7 if winner == 1 else 1
                for pad_idx in range(16):
                    devices[p1_global].set_pad_light(pad_idx, color_p1, on=True)

                p2_global = p2.get_global_device_index(local_dev)
                color_p2 = 7 if winner == 2 else 1
                for pad_idx in range(16):
                    devices[p2_global].set_pad_light(pad_idx, color_p2, on=True)

            time.sleep(1.0)

            break

        # ========================================
        # ОБРАБОТКА PLAYER 1
        # ========================================
        if not p1.finished:
            # Прячем несовпадающие карты P1
            if p1.mismatch_hide_time > 0 and current_time >= p1.mismatch_hide_time:
                # Гасим выбранные карты
                for local_dev, pad_idx in p1.selected:
                    global_dev = p1.get_global_device_index(local_dev)
                    devices[global_dev].set_pad_light(pad_idx, 0, on=False)

                p1.selected = []
                p1.mismatch_hide_time = 0

            # Читаем ввод P1
            if p1.mismatch_hide_time == 0:
                for local_dev in range(2):
                    global_dev = p1.get_global_device_index(local_dev)
                    data = devices[global_dev].device.read(64, timeout_ms=1)
                    if data:
                        pressed = decode_pad_events(data)
                        for pad_idx in pressed:
                            key = (local_dev, pad_idx)

                            # Проверяем: карта существует, не найдена, не выбрана
                            if key in p1.board and key not in p1.matched and key not in p1.selected:
                                p1.selected.append(key)
                                color = p1.board[key]
                                devices[global_dev].set_pad_light(pad_idx, color, on=True)

                                if len(p1.selected) == 2:
                                    # Проверяем пару
                                    key1, key2 = p1.selected
                                    color1 = p1.board[key1]
                                    color2 = p1.board[key2]

                                    if color1 == color2:
                                        # MATCH! Оставляем своим цветом
                                        print(f"  ✅ P1 нашёл пару! (+1)")

                                        # Карты уже горят своим цветом, просто добавляем в matched
                                        p1.matched.add(key1)
                                        p1.matched.add(key2)
                                        p1.score += 1
                                        p1.selected = []

                                        # Проверяем финиш
                                        if len(p1.matched) == 32:
                                            p1.finished = True
                                            p1.finish_time = current_time
                                            print(f"  🏁 P1 ЗАКОНЧИЛ! Счёт: {p1.score}")

                                    else:
                                        # MISMATCH - карты уже горят своими настоящими цветами
                                        # Просто ставим таймер на короткое время
                                        p1.mismatch_hide_time = current_time + MISMATCH_SHOW_TIME

        # ========================================
        # ОБРАБОТКА PLAYER 2
        # ========================================
        if not p2.finished:
            # Прячем несовпадающие карты P2
            if p2.mismatch_hide_time > 0 and current_time >= p2.mismatch_hide_time:
                for local_dev, pad_idx in p2.selected:
                    global_dev = p2.get_global_device_index(local_dev)
                    devices[global_dev].set_pad_light(pad_idx, 0, on=False)

                p2.selected = []
                p2.mismatch_hide_time = 0

            # Читаем ввод P2
            if p2.mismatch_hide_time == 0:
                for local_dev in range(2):
                    global_dev = p2.get_global_device_index(local_dev)
                    data = devices[global_dev].device.read(64, timeout_ms=1)
                    if data:
                        pressed = decode_pad_events(data)
                        for pad_idx in pressed:
                            key = (local_dev, pad_idx)

                            if key in p2.board and key not in p2.matched and key not in p2.selected:
                                p2.selected.append(key)
                                color = p2.board[key]
                                devices[global_dev].set_pad_light(pad_idx, color, on=True)

                                if len(p2.selected) == 2:
                                    key1, key2 = p2.selected
                                    color1 = p2.board[key1]
                                    color2 = p2.board[key2]

                                    if color1 == color2:
                                        # MATCH! Оставляем своим цветом
                                        print(f"  ✅ P2 нашёл пару! (+1)")

                                        # Карты уже горят своим цветом, просто добавляем в matched
                                        p2.matched.add(key1)
                                        p2.matched.add(key2)
                                        p2.score += 1
                                        p2.selected = []

                                        if len(p2.matched) == 32:
                                            p2.finished = True
                                            p2.finish_time = current_time
                                            print(f"  🏁 P2 ЗАКОНЧИЛ! Счёт: {p2.score}")

                                    else:
                                        # MISMATCH - карты уже горят своими настоящими цветами
                                        # Просто ставим таймер на короткое время
                                        p2.mismatch_hide_time = current_time + MISMATCH_SHOW_TIME

        time.sleep(0.001)

    return p1.score, p2.score, p1.finish_time, p2.finish_time


def show_winner(devices, p1_score, p2_score, p1_time, p2_time):
    """Show winner"""
    print("\n" + "=" * 70)
    print("РЕЗУЛЬТАТ")
    print("=" * 70)
    print()
    print(f"  Player 1: {p1_score} пар 🃏")
    print(f"  Player 2: {p2_score} пар 🃏")
    print()

    # Определяем победителя по времени финиша
    if p1_time < p2_time:
        print("🏆 ПОБЕДИТЕЛЬ: Player 1! 🏆 (финишировал первым)")
    elif p2_time < p1_time:
        print("🏆 ПОБЕДИТЕЛЬ: Player 2! 🏆 (финишировал первым)")
    else:
        print("🤝 НИЧЬЯ! 🤝")

    print()

    # Очищаем все устройства
    for dev in devices:
        dev.clear()


def main():
    print("=" * 70)
    print("🃏 MEMORY MATCH - Параллельная игра на память")
    print("=" * 70)
    print()
    print("  🎯 Правила:")
    print("     • 2 игрока играют ОДНОВРЕМЕННО")
    print("     • P1: устройства 1-2 (16 пар, 8×4)")
    print("     • P2: устройства 3-4 (16 пар, 8×4)")
    print("     • Цвета: Red, Yellow, Green, Violet, Blue")
    print("     • Запомни карты за 6 секунд")
    print("     • Открывай 2 карты подряд")
    print("     • Пара → остаются своим цветом, продолжай")
    print("     • Не пара → показываются 0.5с, гаснут")
    print("     • Кто быстрее найдёт все → ПОБЕДИЛ!")
    print()

    # Setup devices with configuration (shows device numbers automatically!)
    print("🔍 Инициализация устройств...")
    sorted_devices = setup_devices_with_config(
        max_count=4,
        show_numbers=True,
        show_duration=0.8
    )

    if len(sorted_devices) != 4:
        print(f"❌ Нужно ровно 4 устройства, найдено {len(sorted_devices)}")
        print()
        print("💡 Совет: Запустите device_setup.py для настройки порядка устройств")
        return

    # Extract devices (already sorted by config)
    devices = [device for device, _ in sorted_devices]

    print()
    print("=" * 70)
    print("✅ Устройства подключены:")
    for device, device_num in sorted_devices:
        player = "P1" if device_num <= 2 else "P2"
        print(f"   Device {device_num} [{player}]: {device.serial}")
    print()
    print("P1: устройства 1-2, P2: устройства 3-4")
    print("=" * 70)

    # Countdown
    print("\nНачинаем через:")
    show_countdown(devices)

    try:
        while True:
            p1_score, p2_score, p1_time, p2_time = play_round(devices)
            show_winner(devices, p1_score, p2_score, p1_time, p2_time)

            print("\n" + "=" * 70)
            print("🔄 РЕВАНШ: Нажми любой пэд")
            print("   (или Ctrl+C для выхода)")
            print()

            waiting = True
            while waiting:
                for dev in devices:
                    data = dev.device.read(64, timeout_ms=100)
                    if data and decode_pad_events(data):
                        waiting = False
                        break
                time.sleep(0.01)

            for dev in devices:
                dev.clear()

            print("\n" + "=" * 70)
            print("Новый раунд!")
            show_countdown(devices)

    except KeyboardInterrupt:
        print("\n\nВыход...")
    finally:
        for dev in devices:
            dev.close()
        print("🎉 Игра окончена!")


if __name__ == "__main__":
    main()
