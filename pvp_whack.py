#!/usr/bin/env python3
"""
Maschine Mikro MK3 PvP Whack-a-Mole
====================================

2 игрока соревнуются кто быстрее бьёт горящие пэды!
Игрок 1: устройства 1-2 (слева)
Игрок 2: устройства 3-4 (справа)

Использует модуль maschine для управления устройствами.
"""

import time
import random
from maschine import setup_devices_with_config, Color, PadEventType
from maschine.screen import Screen, SCREEN_WIDTH, SCREEN_HEIGHT
from maschine.screen_font import draw_text_5x7, draw_digit

# Colors
COLOR_P1_TARGET = Color.CYAN      # Cyan - цель игрока 1
COLOR_P2_TARGET = Color.MAGENTA   # Magenta - цель игрока 2
COLOR_GOLDEN = Color.WARM_YELLOW  # Warm Yellow - ЗОЛОТАЯ ЦЕЛЬ (для обоих!)
COLOR_HIT = Color.GREEN           # Green - успешное попадание
COLOR_MISS = Color.RED            # Red - промах

# Game settings
ROUND_DURATION = 45      # секунд на раунд
SPAWN_INTERVAL = 0.6     # как часто появляются новые цели
TARGETS_PER_SPAWN = 3    # сколько целей за раз
PAD_LIFETIME = 2.0       # сколько цель горит перед исчезновением
GOLDEN_SPAWN_INTERVAL = 6.0  # как часто появляется ЗОЛОТАЯ цель
GOLDEN_LIFETIME = 3.0    # золотая цель живёт дольше!

# Button LED indices
BUTTON_PLAY = 22


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

        if event_type in [PadEventType.PRESS_ON, PadEventType.NOTE_ON]:
            events.append(pad_idx)

    return events


def wait_for_play_button(devices):
    """Wait for PLAY button press on any device"""
    print("⏯️  Нажмите PLAY для начала...")

    # Light up PLAY button on all devices
    for dev in devices:
        with dev.lock:
            dev.led_buffer[1 + BUTTON_PLAY] = 0x7f
            dev.device.write(dev.led_buffer)

    while True:
        for dev in devices:
            data = dev.device.read(64, timeout_ms=10)
            if data and data[0] == 0x01:
                # Check if any button is pressed
                # We'll accept any button press for simplicity
                has_button = any(data[i] != 0 for i in range(1, min(5, len(data))))
                if has_button:
                    # Clear PLAY button lights
                    for d in devices:
                        with d.lock:
                            d.led_buffer[1 + BUTTON_PLAY] = 0x00
                            d.device.write(d.led_buffer)
                    # Clear any accumulated pad events after button press
                    time.sleep(0.1)
                    for d in devices:
                        # Drain the HID buffer
                        while d.device.read(64, timeout_ms=1):
                            pass
                    return
        time.sleep(0.01)


def display_final_scores(devices, p1_score, p2_score, p1_hits, p1_misses, p2_hits, p2_misses, p1_golden, p2_golden):
    """Display final scores on all screens"""
    # Player 1 devices - show P1 results
    for dev in devices[:2]:
        screen = Screen()
        screen.clear()

        # Draw border
        screen.draw_rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, filled=False, on=True)

        # P1 score (large)
        draw_text_5x7(screen, 3, 2, "P1", scale=1)
        score_str = str(p1_score)
        draw_text_5x7(screen, 25, 2, score_str, scale=2)

        # Hits/Golden/Misses (small)
        draw_text_5x7(screen, 3, 15, f"H{p1_hits}", scale=1)
        draw_text_5x7(screen, 25, 15, f"G{p1_golden}", scale=1)
        draw_text_5x7(screen, 50, 15, f"M{p1_misses}", scale=1)

        screen.write(dev.device)

    # Player 2 devices - show P2 results
    for dev in devices[2:]:
        screen = Screen()
        screen.clear()

        # Draw border
        screen.draw_rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, filled=False, on=True)

        # P2 score (large)
        draw_text_5x7(screen, 3, 2, "P2", scale=1)
        score_str = str(p2_score)
        draw_text_5x7(screen, 25, 2, score_str, scale=2)

        # Hits/Golden/Misses (small)
        draw_text_5x7(screen, 3, 15, f"H{p2_hits}", scale=1)
        draw_text_5x7(screen, 25, 15, f"G{p2_golden}", scale=1)
        draw_text_5x7(screen, 50, 15, f"M{p2_misses}", scale=1)

        screen.write(dev.device)


def display_ready_state(devices):
    """Display READY state on all screens"""
    for dev in devices:
        screen = Screen()
        screen.clear()

        # Draw border
        screen.draw_rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, filled=False, on=True)

        # Draw READY text
        draw_text_5x7(screen, 10, 8, "READY", scale=2)

        screen.write(dev.device)


class Target:
    """Активная цель"""
    def __init__(self, device_idx, pad_idx):
        self.device_idx = device_idx
        self.pad_idx = pad_idx
        self.spawn_time = time.time()

    def is_expired(self):
        return (time.time() - self.spawn_time) > PAD_LIFETIME


class FlashEffect:
    """Визуальный эффект вспышки (неблокирующий)"""
    def __init__(self, device, pad_idx, color_idx, duration=0.08):
        self.device = device
        self.pad_idx = pad_idx
        self.color_idx = color_idx
        self.end_time = time.time() + duration
        # Сразу зажигаем
        self.device.set_pad_light(pad_idx, color_idx, on=True)

    def is_expired(self):
        return time.time() >= self.end_time

    def clear(self):
        self.device.set_pad_light(self.pad_idx, self.color_idx, on=False)


def show_countdown(devices):
    """Show countdown 3, 2, 1, GO!"""
    for num in [3, 2, 1]:
        print(f"  {num}...")
        # Flash all
        for dev in devices:
            dev.set_all_pads(Color.WHITE)
        time.sleep(0.3)
        for dev in devices:
            dev.clear()
        time.sleep(0.4)

    print("  GO!")
    for dev in devices:
        dev.set_all_pads(Color.GREEN)
    time.sleep(0.3)
    for dev in devices:
        dev.clear()


class GoldenTarget:
    """Золотая цель - доступна обоим игрокам!"""
    def __init__(self, device_idx, pad_idx, is_p1_side):
        self.device_idx = device_idx
        self.pad_idx = pad_idx
        self.is_p1_side = is_p1_side  # На чьей стороне появилась
        self.spawn_time = time.time()

    def is_expired(self):
        return (time.time() - self.spawn_time) > GOLDEN_LIFETIME


def play_round(devices):
    """Play one round"""
    p1_devices = devices[:2]  # Player 1: devices 0-1
    p2_devices = devices[2:]  # Player 2: devices 2-3

    p1_score = 0
    p2_score = 0
    p1_hits = 0
    p1_misses = 0
    p2_hits = 0
    p2_misses = 0
    p1_golden = 0
    p2_golden = 0

    p1_targets = {}  # (dev_idx, pad_idx) -> Target
    p2_targets = {}
    golden_targets = {}  # (side, dev_idx, pad_idx) -> GoldenTarget

    active_effects = []  # Активные вспышки (неблокирующие)

    start_time = time.time()
    last_spawn_time = time.time()
    last_golden_spawn = time.time()
    last_print_time = start_time

    print("\n⚔️  FIGHT!")
    print()

    # Main game loop (неблокирующий - простой и быстрый)
    while time.time() - start_time < ROUND_DURATION:
        current_time = time.time()
        remaining = ROUND_DURATION - (current_time - start_time)

        # Update visual effects (неблокирующая очистка)
        for effect in list(active_effects):
            if effect.is_expired():
                effect.clear()
                active_effects.remove(effect)

        # Spawn new targets (несколько сразу!)
        if current_time - last_spawn_time > SPAWN_INTERVAL:
            last_spawn_time = current_time

            # Spawn multiple targets for P1 (Cyan)
            for _ in range(TARGETS_PER_SPAWN):
                dev_idx = random.randint(0, 1)
                pad_idx = random.randint(0, 15)
                key = (dev_idx, pad_idx)
                if key not in p1_targets and ('p1', dev_idx, pad_idx) not in golden_targets:
                    p1_targets[key] = Target(dev_idx, pad_idx)
                    p1_devices[dev_idx].set_pad_light(pad_idx, COLOR_P1_TARGET, on=True)

            # Spawn multiple targets for P2 (Magenta)
            for _ in range(TARGETS_PER_SPAWN):
                dev_idx = random.randint(0, 1)
                pad_idx = random.randint(0, 15)
                key = (dev_idx, pad_idx)
                if key not in p2_targets and ('p2', dev_idx, pad_idx) not in golden_targets:
                    p2_targets[key] = Target(dev_idx, pad_idx)
                    p2_devices[dev_idx].set_pad_light(pad_idx, COLOR_P2_TARGET, on=True)

        # Spawn GOLDEN targets! 💛✨
        if current_time - last_golden_spawn > GOLDEN_SPAWN_INTERVAL:
            last_golden_spawn = current_time

            # Spawn на стороне P1
            dev_idx = random.randint(0, 1)
            pad_idx = random.randint(0, 15)
            key = ('p1', dev_idx, pad_idx)
            if key not in golden_targets:
                golden_targets[key] = GoldenTarget(dev_idx, pad_idx, is_p1_side=True)
                p1_devices[dev_idx].set_pad_light(pad_idx, COLOR_GOLDEN, on=True)

            # Spawn на стороне P2
            dev_idx = random.randint(0, 1)
            pad_idx = random.randint(0, 15)
            key = ('p2', dev_idx, pad_idx)
            if key not in golden_targets:
                golden_targets[key] = GoldenTarget(dev_idx, pad_idx, is_p1_side=False)
                p2_devices[dev_idx].set_pad_light(pad_idx, COLOR_GOLDEN, on=True)

        # Check expired targets (гасим те что не успели!)
        for key, target in list(p1_targets.items()):
            if target.is_expired():
                dev_idx, pad_idx = key
                active_effects.append(FlashEffect(
                    p1_devices[dev_idx],
                    pad_idx,
                    COLOR_MISS,
                    duration=0.12
                ))
                del p1_targets[key]

        for key, target in list(p2_targets.items()):
            if target.is_expired():
                dev_idx, pad_idx = key
                active_effects.append(FlashEffect(
                    p2_devices[dev_idx],
                    pad_idx,
                    COLOR_MISS,
                    duration=0.12
                ))
                del p2_targets[key]

        # Check expired GOLDEN targets
        for key, target in list(golden_targets.items()):
            if target.is_expired():
                side, dev_idx, pad_idx = key
                devices_list = p1_devices if side == 'p1' else p2_devices
                active_effects.append(FlashEffect(
                    devices_list[dev_idx],
                    pad_idx,
                    COLOR_MISS,
                    duration=0.12
                ))
                del golden_targets[key]

        # Check P1 presses (неблокирующая обработка!)
        for dev_idx, dev in enumerate(p1_devices):
            data = dev.device.read(64, timeout_ms=2)
            if data:
                pressed = decode_pad_events(data)
                for pad_idx in pressed:
                    key = (dev_idx, pad_idx)
                    golden_key = ('p1', dev_idx, pad_idx)

                    if golden_key in golden_targets:
                        # GOLDEN HIT! +2 очка! 💛✨
                        p1_score += 2
                        p1_hits += 1
                        p1_golden += 1
                        # Яркая золотая вспышка!
                        active_effects.append(FlashEffect(dev, pad_idx, COLOR_GOLDEN, duration=0.15))
                        del golden_targets[golden_key]
                    elif key in p1_targets:
                        # HIT! +1 очко
                        p1_score += 1
                        p1_hits += 1
                        active_effects.append(FlashEffect(dev, pad_idx, COLOR_HIT, duration=0.1))
                        del p1_targets[key]
                    else:
                        # MISS! -1 очко
                        p1_score -= 1
                        p1_misses += 1
                        active_effects.append(FlashEffect(dev, pad_idx, COLOR_MISS, duration=0.15))

        # Check P2 presses (неблокирующая обработка!)
        for dev_idx, dev in enumerate(p2_devices):
            data = dev.device.read(64, timeout_ms=2)
            if data:
                pressed = decode_pad_events(data)
                for pad_idx in pressed:
                    key = (dev_idx, pad_idx)
                    golden_key = ('p2', dev_idx, pad_idx)

                    if golden_key in golden_targets:
                        # GOLDEN HIT! +2 очка! 💛✨
                        p2_score += 2
                        p2_hits += 1
                        p2_golden += 1
                        # Яркая золотая вспышка!
                        active_effects.append(FlashEffect(dev, pad_idx, COLOR_GOLDEN, duration=0.15))
                        del golden_targets[golden_key]
                    elif key in p2_targets:
                        # HIT! +1 очко
                        p2_score += 1
                        p2_hits += 1
                        active_effects.append(FlashEffect(dev, pad_idx, COLOR_HIT, duration=0.1))
                        del p2_targets[key]
                    else:
                        # MISS! -1 очко
                        p2_score -= 1
                        p2_misses += 1
                        active_effects.append(FlashEffect(dev, pad_idx, COLOR_MISS, duration=0.15))

        # Print score every 5 seconds
        if current_time - last_print_time >= 5:
            last_print_time = current_time
            print(f"⏱️  {int(remaining)}s | P1: {p1_score} | P2: {p2_score}")

        # Минимальная пауза для снижения нагрузки на CPU
        time.sleep(0.001)

    # Clear all targets
    for dev in devices:
        dev.clear()

    # Display final scores on screens
    display_final_scores(devices, p1_score, p2_score, p1_hits, p1_misses, p2_hits, p2_misses, p1_golden, p2_golden)

    return p1_score, p2_score, p1_hits, p1_misses, p2_hits, p2_misses, p1_golden, p2_golden


def show_winner(devices, p1_score, p2_score, p1_hits, p1_misses, p2_hits, p2_misses, p1_golden, p2_golden):
    """Show winner"""
    print("\n" + "=" * 70)
    print("РЕЗУЛЬТАТ")
    print("=" * 70)
    print()
    print(f"  Player 1 (Cyan):")
    print(f"    Счёт:      {p1_score} очков")
    print(f"    Попадания: {p1_hits} 🟢")
    print(f"    ЗОЛОТЫЕ:   {p1_golden} 💛")
    print(f"    Промахи:   {p1_misses} 🔴")
    print()
    print(f"  Player 2 (Magenta):")
    print(f"    Счёт:      {p2_score} очков")
    print(f"    Попадания: {p2_hits} 🟢")
    print(f"    ЗОЛОТЫЕ:   {p2_golden} 💛")
    print(f"    Промахи:   {p2_misses} 🔴")
    print()

    if p1_score > p2_score:
        winner = "Player 1"
        winner_devices = devices[:2]
        loser_devices = devices[2:]
        print("🏆 ПОБЕДИТЕЛЬ: Player 1! 🏆")
    elif p2_score > p1_score:
        winner = "Player 2"
        winner_devices = devices[2:]
        loser_devices = devices[:2]
        print("🏆 ПОБЕДИТЕЛЬ: Player 2! 🏆")
    else:
        winner = "НИЧЬЯ"
        winner_devices = devices
        loser_devices = []
        print("🤝 НИЧЬЯ! 🤝")

    print()

    # Victory animation
    if winner != "НИЧЬЯ":
        for _ in range(6):
            # Winner devices = GREEN
            for dev in winner_devices:
                dev.set_all_pads(COLOR_HIT)
            # Loser devices = RED
            for dev in loser_devices:
                dev.set_all_pads(COLOR_MISS)
            time.sleep(0.3)

            for dev in devices:
                dev.clear()
            time.sleep(0.2)
    else:
        # Draw animation - both blink green
        for _ in range(6):
            for dev in devices:
                dev.set_all_pads(COLOR_HIT)
            time.sleep(0.3)
            for dev in devices:
                dev.clear()
            time.sleep(0.2)


def main():
    print("=" * 70)
    print("⚔️  PvP WHACK-A-MOLE - Maschine Mikro MK3")
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
    print("ПРАВИЛА")
    print("=" * 70)
    print()
    print("  👥 2 игрока:")
    print("     Player 1: устройства 1-2 (слева) - цели CYAN 🔵")
    print("     Player 2: устройства 3-4 (справа) - цели MAGENTA 💜")
    print()
    print(f"  ⏱️  Время раунда: {ROUND_DURATION} секунд")
    print()
    print(f"  ⚡ Динамика:")
    print(f"     • Появляется по {TARGETS_PER_SPAWN} цели одновременно")
    print(f"     • У каждой цели {PAD_LIFETIME}s жизни")
    print()
    print("  🎯 Правила:")
    print("     • P1: цели CYAN (голубые) 🔵")
    print("     • P2: цели MAGENTA (розовые) 💜")
    print("     • ЗОЛОТАЯ цель: +2 очка! 💛✨")
    print("     • Попал = +1 очко + зелёная вспышка 🟢")
    print("     • Промах = -1 очко + красная вспышка 🔴")
    print("     • Не успел = цель гаснет красным 🔴")
    print("     • Кто больше очков = ПОБЕДИЛ!")
    print()
    print("  🏆 Финал:")
    print("     • Победитель: устройства горят ЗЕЛЁНЫМ")
    print("     • Проигравший: устройства горят КРАСНЫМ")
    print()
    print("  🎮 Управление:")
    print("     • PLAY: начать игру / новый раунд")
    print()
    print("=" * 70)
    print()

    # Show ready state and wait for PLAY button
    display_ready_state(devices)
    wait_for_play_button(devices)
    print()

    # Countdown
    print("Приготовься!")
    show_countdown(devices)

    try:
        while True:  # Бесконечный реванш!
            # Play round
            p1_score, p2_score, p1_hits, p1_misses, p2_hits, p2_misses, p1_golden, p2_golden = play_round(devices)

            # Show winner
            show_winner(devices, p1_score, p2_score, p1_hits, p1_misses, p2_hits, p2_misses, p1_golden, p2_golden)

            print("\n" + "=" * 70)
            print()
            print("🔄 РЕВАНШ: Нажмите PLAY для продолжения")
            print("   (или Ctrl+C для выхода)")
            print()

            # Wait for PLAY button
            display_ready_state(devices)
            wait_for_play_button(devices)

            # Clear all
            for dev in devices:
                dev.clear()

            print("\n" + "=" * 70)
            print()

            # New countdown
            print("Новый раунд!")
            show_countdown(devices)

    except KeyboardInterrupt:
        print("\n\n🛑 Игра прервана")

    finally:
        print("\nОчистка...")
        for dev in devices:
            # Clear pads
            dev.clear()
            # Clear screen
            screen = Screen()
            screen.clear()
            screen.write(dev.device)
            # Close device
            dev.close()
        print("✓ Готово\n")


if __name__ == "__main__":
    main()

