#!/usr/bin/env python3
"""
Maschine Mikro MK3 Reaction Game
=================================

Игра на реакцию: нажимай горящие пэды как можно быстрее!

Использует модуль maschine для управления устройствами.
"""

import time
import random
from maschine import setup_devices_with_config, Color, PadEventType

# Colors
COLOR_TARGET = Color.RED    # Red - целевые пэды
COLOR_SUCCESS = Color.GREEN  # Green - успешно нажато

# Game settings
ROUNDS = 10
COUNTDOWN_START = 5

# Font for numbers
FONT = {
    '0': [[1,1,1], [1,0,1], [1,0,1], [1,1,1]],
    '1': [[0,1,0], [1,1,0], [0,1,0], [1,1,1]],
    '2': [[1,1,1], [0,0,1], [1,1,1], [1,0,0], [1,1,1]],  # 5 cols
    '3': [[1,1,1], [0,0,1], [1,1,1], [0,0,1], [1,1,1]],  # 5 cols
    '4': [[1,0,1], [1,0,1], [1,1,1], [0,0,1]],
    '5': [[1,1,1], [1,0,0], [1,1,1], [0,0,1], [1,1,1]],  # 5 cols
    ' ': [[0,0,0], [0,0,0], [0,0,0], [0,0,0]],
}


def decode_pad_events(data):
    """Decode pad press events"""
    if not data or data[0] != 0x02:
        return []

    events = []
    for i in range(1, len(data), 3):
        pad_idx = data[i]
        event_byte = data[i + 1]
        vel_low = data[i + 2]

        if i > 1 and pad_idx == 0 and event_byte == 0 and vel_low == 0:
            break

        event_type = event_byte & 0xf0

        # Press events
        if event_type in [PadEventType.PRESS_ON, PadEventType.NOTE_ON]:
            events.append(pad_idx)

    return events


def text_to_bitmap(text):
    """Convert text to bitmap"""
    columns = []
    for char in text:
        if char in FONT:
            char_data = FONT[char]
            width = len(char_data[0])
            for col_idx in range(width):
                col = [char_data[row][col_idx] for row in range(4)]
                columns.append(col)
            columns.append([0, 0, 0, 0])
    return columns


def show_text(devices, text, color_idx, duration=2):
    """Show scrolling text"""
    bitmap = text_to_bitmap(text)
    start_time = time.time()
    offset = 0

    while time.time() - start_time < duration:
        patterns = []
        for device_idx in range(4):
            pattern = [0] * 16
            for col in range(4):
                global_col = offset + (device_idx * 4) + col
                if global_col < len(bitmap):
                    column = bitmap[global_col]
                    for row in range(4):
                        pad_idx = row * 4 + col
                        pattern[pad_idx] = column[row]
            patterns.append(pattern)

        for dev_idx, dev in enumerate(devices):
            dev.set_pattern(patterns[dev_idx], color_idx)

        time.sleep(0.15)
        offset += 1
        if offset >= len(bitmap):
            offset = 0


def show_countdown(devices):
    """Show countdown 5, 4, 3, 2, 1"""
    for num in range(COUNTDOWN_START, 0, -1):
        print(f"  {num}...")
        show_text(devices, f" {num} ", Color.WHITE, duration=0.8)  # White

    # GO!
    print("  GO!")
    show_text(devices, " ", Color.GREEN, duration=0.3)  # Flash green
    for dev in devices:
        dev.clear()


def calculate_score(reaction_time, num_targets):
    """
    Calculate score based on reaction time

    Score system:
    - < 0.5s: 100 points
    - 0.5-0.7s: 80 points
    - 0.7-1.0s: 60 points
    - 1.0-1.5s: 40 points
    - > 1.5s: 20 points

    Bonus: +10 points per target pad
    """
    base_score = 0

    if reaction_time < 0.5:
        base_score = 100
    elif reaction_time < 0.7:
        base_score = 80
    elif reaction_time < 1.0:
        base_score = 60
    elif reaction_time < 1.5:
        base_score = 40
    else:
        base_score = 20

    # Bonus for multiple targets
    bonus = (num_targets - 1) * 10

    return base_score + bonus


def play_round(devices, round_num):
    """Play one round of the game"""
    # Pick random pads (1-4 pads)
    num_targets = random.randint(1, 4)

    # Pick random device and pads on it
    target_device_idx = random.randint(0, 3)
    target_pads = random.sample(range(16), num_targets)

    # Light up target pads
    for pad_idx in target_pads:
        devices[target_device_idx].set_pad_light(pad_idx, COLOR_TARGET, on=True)

    # Start timing
    start_time = time.time()
    hit_pads = set()

    print(f"\n[Раунд {round_num}] Нажми {num_targets} {'пэд' if num_targets == 1 else 'пэда' if num_targets < 5 else 'пэдов'}!", flush=True)

    # Wait for all pads to be hit
    while len(hit_pads) < num_targets:
        data = devices[target_device_idx].device.read(64, timeout_ms=10)

        if data:
            pressed_pads = decode_pad_events(data)

            for pad_idx in pressed_pads:
                if pad_idx in target_pads and pad_idx not in hit_pads:
                    hit_pads.add(pad_idx)
                    # Change to green
                    devices[target_device_idx].set_pad_light(pad_idx, COLOR_SUCCESS, on=True)

        time.sleep(0.001)

    # Calculate reaction time and score
    reaction_time = time.time() - start_time
    score = calculate_score(reaction_time, num_targets)

    # Clear all
    time.sleep(0.2)
    devices[target_device_idx].clear()

    return reaction_time, score


def show_results(devices, times, scores):
    """Show game results"""
    avg_time = sum(times) / len(times)
    best_time = min(times)
    worst_time = max(times)
    total_score = sum(scores)

    print("\n" + "=" * 70)
    print("РЕЗУЛЬТАТЫ")
    print("=" * 70)
    print()
    print(f"💯 ОБЩИЙ СЧЁТ: {total_score} очков")
    print()
    print("Времена:")
    print(f"  Среднее: {avg_time:.3f} сек")
    print(f"  Лучшее:  {best_time:.3f} сек")
    print(f"  Худшее:  {worst_time:.3f} сек")
    print()
    print("Детали по раундам:")
    for i, (t, s) in enumerate(zip(times, scores), 1):
        stars = "⭐" * (s // 25)  # звёздочки за очки
        print(f"  Раунд {i:2d}: {t:.3f}s = {s:3d} очков {stars}")
    print()

    # Rank based on score
    if total_score >= 900:
        rank = "МАСТЕР! 🏆"
        rank_color = Color.WHITE
    elif total_score >= 800:
        rank = "ЭКСПЕРТ! 🥇"
        rank_color = Color.YELLOW
    elif total_score >= 700:
        rank = "ПРОФИ! 🥈"
        rank_color = Color.CYAN
    elif total_score >= 600:
        rank = "ХОРОШО! 🥉"
        rank_color = Color.GREEN
    else:
        rank = "ТРЕНИРУЙСЯ! 💪"
        rank_color = Color.RED

    print(f"Твой ранг: {rank}")
    print()

    # Show scrolling results on display
    result_text = f"  SCORE {total_score}  "

    print("Показываю результаты на дисплее...")
    for _ in range(2):
        show_text(devices, result_text, rank_color, duration=3)


def main():
    print("=" * 70)
    print("🎮 REACTION GAME - Maschine Mikro MK3")
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

    print("\n✅ Устройства готовы!")
    print()
    print("=" * 70)
    print("ПРАВИЛА ИГРЫ")
    print("=" * 70)
    print()
    print(f"  • {ROUNDS} раундов")
    print("  • В каждом раунде загорятся 1-4 пэда")
    print("  • Нажми все горящие пэды как можно быстрее!")
    print()
    print("СИСТЕМА ОЧКОВ:")
    print("  < 0.5 сек  = 100 очков 🔥")
    print("  0.5-0.7 с  = 80 очков ⚡")
    print("  0.7-1.0 с  = 60 очков 👍")
    print("  1.0-1.5 с  = 40 очков 💪")
    print("  > 1.5 сек  = 20 очков")
    print("  Бонус: +10 за каждый дополнительный пэд")
    print()
    print("=" * 70)
    print()
    input("Нажми Enter для начала...")
    print()

    # Countdown
    print("Приготовься!")
    show_countdown(devices)

    # Play rounds
    times = []
    scores = []

    try:
        for round_num in range(1, ROUNDS + 1):
            reaction_time, score = play_round(devices, round_num)
            times.append(reaction_time)
            scores.append(score)

            # Show result for this round
            if score >= 90:
                emoji = "🔥"
            elif score >= 70:
                emoji = "⚡"
            elif score >= 50:
                emoji = "👍"
            else:
                emoji = "💪"

            print(f"  ⏱️  {reaction_time:.3f}s = {score} очков {emoji}")
            time.sleep(1)

        # Show results
        show_results(devices, times, scores)

        print("\n🎉 Игра завершена!")

    except KeyboardInterrupt:
        print("\n\n🛑 Игра прервана")

    finally:
        print("\nОчистка...")
        for dev in devices:
            dev.close()
        print("✓ Готово\n")


if __name__ == "__main__":
    main()

