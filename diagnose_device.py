#!/usr/bin/env python3
"""
🔍 Диагностика устройства Maschine Mikro MK3
=============================================

Показывает RAW события с пэдов без MIDI обработки.
Помогает определить аппаратные проблемы.

Использование:
    python3 diagnose_device.py           # Тестировать все устройства
    python3 diagnose_device.py 2         # Тестировать только Device 2
"""

import sys
import time
import threading
from collections import defaultdict
from maschine import (
    setup_devices_with_config,
    PadEventType,
    Color,
    PAD_COUNT,
)

# Тест длится 30 секунд
TEST_DURATION = 30


class DeviceDiagnostics:
    """Диагностика одного устройства"""

    def __init__(self, device, device_num):
        self.device = device
        self.device_num = device_num
        self.running = False
        self.thread = None

        # Статистика
        self.events_per_pad = defaultdict(int)  # pad_idx -> count
        self.note_on_per_pad = defaultdict(int)  # pad_idx -> ON count
        self.note_off_per_pad = defaultdict(int)  # pad_idx -> OFF count
        self.low_velocity_per_pad = defaultdict(int)  # pad_idx -> low velocity count
        self.velocities_per_pad = defaultdict(list)  # pad_idx -> [velocities]
        self.note_on_count = 0
        self.note_off_count = 0
        self.total_events = 0
        self.low_velocity_count = 0
        self.last_event_time = None
        self.last_event_time_per_pad = {}  # pad_idx -> last time
        self.event_gaps = []  # Gaps between events in ms
        self.event_gaps_per_pad = defaultdict(list)  # pad_idx -> [gaps]

    def start(self):
        self.running = True
        # Подсветить устройство
        self.device.set_all_pads(Color.CYAN, brightness=0x7f)
        self.thread = threading.Thread(target=self._read_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        self.device.clear()

    def _read_loop(self):
        while self.running:
            try:
                data = self.device.device.read(64, timeout_ms=5)
            except Exception:
                continue

            if not data or len(data) < 1:
                continue

            report_id = data[0]

            if report_id != 0x02:  # Only pad events
                continue

            now = time.time()

            for i in range(1, len(data), 3):
                if i + 2 >= len(data):
                    break

                pad_idx = data[i]
                event_byte = data[i + 1]
                velocity_low = data[i + 2]

                if pad_idx == 0 and event_byte == 0:
                    break

                event_type = event_byte & 0xf0

                if not (0 <= pad_idx < PAD_COUNT):
                    continue

                # Calculate velocity
                velocity_12bit = ((event_byte & 0x0f) << 8) | velocity_low
                velocity = min(127, velocity_12bit >> 5)

                # Track statistics
                self.total_events += 1
                self.events_per_pad[pad_idx] += 1

                if event_type in (PadEventType.PRESS_ON, PadEventType.NOTE_ON):
                    self.note_on_count += 1
                    self.note_on_per_pad[pad_idx] += 1
                    self.velocities_per_pad[pad_idx].append(velocity)

                    if velocity < 5:
                        self.low_velocity_count += 1
                        self.low_velocity_per_pad[pad_idx] += 1

                    # Visual feedback
                    self.device.set_pad_light(pad_idx, Color.WHITE, brightness=0x7f, on=True)

                    # Track event gaps (global)
                    if self.last_event_time:
                        gap_ms = (now - self.last_event_time) * 1000
                        self.event_gaps.append(gap_ms)
                    self.last_event_time = now

                    # Track event gaps (per pad)
                    if pad_idx in self.last_event_time_per_pad:
                        gap_ms = (now - self.last_event_time_per_pad[pad_idx]) * 1000
                        self.event_gaps_per_pad[pad_idx].append(gap_ms)
                    self.last_event_time_per_pad[pad_idx] = now

                    # Print event
                    print(f"D{self.device_num} Pad {pad_idx:2d} ON  v{velocity:3d}")

                elif event_type in (PadEventType.PRESS_OFF, PadEventType.NOTE_OFF):
                    self.note_off_count += 1
                    self.note_off_per_pad[pad_idx] += 1
                    self.device.set_pad_light(pad_idx, Color.CYAN, brightness=0x7f, on=True)

    def get_report(self):
        """Получить отчёт о диагностике"""
        lines = []
        lines.append(f"\n{'='*60}")
        lines.append(f"📊 Device {self.device_num} ({self.device.serial})")
        lines.append(f"{'='*60}")
        lines.append(f"  Total events:    {self.total_events}")
        lines.append(f"  Note ON:         {self.note_on_count}")
        lines.append(f"  Note OFF:        {self.note_off_count}")
        lines.append(f"  Low velocity (<5): {self.low_velocity_count}")

        if self.note_on_count > 0 and self.note_off_count > 0:
            ratio = self.note_on_count / self.note_off_count
            if ratio > 1.2:
                lines.append(f"  ⚠️  ON/OFF ratio: {ratio:.2f} (missing Note OFF events!)")
            elif ratio < 0.8:
                lines.append(f"  ⚠️  ON/OFF ratio: {ratio:.2f} (missing Note ON events!)")
            else:
                lines.append(f"  ✅ ON/OFF ratio: {ratio:.2f} (normal)")

        if self.event_gaps:
            avg_gap = sum(self.event_gaps) / len(self.event_gaps)
            min_gap = min(self.event_gaps)
            max_gap = max(self.event_gaps)
            lines.append(f"  Event gaps (ms): avg={avg_gap:.1f}, min={min_gap:.1f}, max={max_gap:.1f}")

        # Per-pad breakdown
        if self.events_per_pad:
            lines.append(f"\n  📊 Детальная статистика по пэдам:")
            lines.append(f"  {'Pad':>4} {'ON':>6} {'OFF':>6} {'Ratio':>7} {'LowVel':>7} {'AvgVel':>7} {'MinGap':>8} {'Status'}")
            lines.append(f"  {'-'*4} {'-'*6} {'-'*6} {'-'*7} {'-'*7} {'-'*7} {'-'*8} {'-'*10}")

            for pad_idx in sorted(self.events_per_pad.keys()):
                on_count = self.note_on_per_pad[pad_idx]
                off_count = self.note_off_per_pad[pad_idx]
                low_vel = self.low_velocity_per_pad[pad_idx]

                # ON/OFF ratio
                if off_count > 0:
                    ratio = on_count / off_count
                    ratio_str = f"{ratio:.2f}"
                else:
                    ratio_str = "N/A"

                # Average velocity
                velocities = self.velocities_per_pad[pad_idx]
                if velocities:
                    avg_vel = sum(velocities) / len(velocities)
                    avg_vel_str = f"{avg_vel:.0f}"
                else:
                    avg_vel_str = "N/A"

                # Min gap between events (fast playing detection)
                gaps = self.event_gaps_per_pad[pad_idx]
                if gaps:
                    min_gap = min(gaps)
                    min_gap_str = f"{min_gap:.1f}ms"
                else:
                    min_gap_str = "N/A"

                # Status
                status = "✅"
                if on_count > 0 and off_count > 0:
                    ratio = on_count / off_count
                    if ratio > 1.3 or ratio < 0.7:
                        status = "⚠️ ratio"
                if low_vel > on_count * 0.1:  # >10% low velocity
                    status = "⚠️ lowvel"

                lines.append(f"  {pad_idx:4d} {on_count:6d} {off_count:6d} {ratio_str:>7} {low_vel:7d} {avg_vel_str:>7} {min_gap_str:>8} {status}")

        return '\n'.join(lines)


def main():
    # Parse arguments
    target_device = None
    if len(sys.argv) > 1:
        try:
            target_device = int(sys.argv[1])
        except ValueError:
            print(f"Usage: {sys.argv[0]} [device_number]")
            return

    print("=" * 60)
    print("🔍 Maschine Mikro MK3 — Диагностика устройств")
    print("=" * 60)
    print()

    sorted_devices = setup_devices_with_config(
        max_count=4,
        show_numbers=True,
        show_duration=0.3
    )

    if not sorted_devices:
        print("❌ Устройства не найдены")
        return

    # Filter to target device if specified
    if target_device:
        sorted_devices = [(d, n) for d, n in sorted_devices if n == target_device]
        if not sorted_devices:
            print(f"❌ Device {target_device} не найден")
            return

    print(f"\n🎯 Тестирование: {len(sorted_devices)} устройств")
    print(f"⏱️  Длительность: {TEST_DURATION} секунд")
    print()
    print("👉 Играй на пэдах! Особенно на проблемных.")
    print("   Попробуй быстрые восьмые на Pad 12 (верхний левый)")
    print()
    print("-" * 60)

    # Create diagnostics
    diagnostics = []
    for device, device_num in sorted_devices:
        diag = DeviceDiagnostics(device, device_num)
        diagnostics.append(diag)
        diag.start()

    # Wait for test duration
    try:
        for remaining in range(TEST_DURATION, 0, -1):
            print(f"\r⏱️  Осталось: {remaining} сек...", end='', flush=True)
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n🛑 Прервано")

    print("\n")

    # Stop and collect reports
    for diag in diagnostics:
        diag.stop()

    # Print reports
    print("\n" + "=" * 60)
    print("📋 РЕЗУЛЬТАТЫ ДИАГНОСТИКИ")
    print("=" * 60)

    for diag in diagnostics:
        print(diag.get_report())

    # Comparison
    if len(diagnostics) > 1:
        print(f"\n{'='*60}")
        print("🔬 СРАВНЕНИЕ УСТРОЙСТВ")
        print(f"{'='*60}")

        total_events = [(d.device_num, d.note_on_count) for d in diagnostics]
        total_events.sort(key=lambda x: x[1], reverse=True)

        if total_events[0][1] > 0:
            best = total_events[0][1]
            for device_num, count in total_events:
                pct = (count / best) * 100 if best > 0 else 0
                status = "✅" if pct > 80 else "⚠️" if pct > 50 else "❌"
                print(f"  Device {device_num}: {count:4d} events ({pct:5.1f}%) {status}")

    # Cleanup
    for device, _ in sorted_devices:
        device.close()

    print("\n✅ Диагностика завершена\n")


if __name__ == "__main__":
    main()

