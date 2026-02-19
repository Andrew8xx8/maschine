#!/usr/bin/env python3
"""
🎹 Maschine MK3 → MIDI Bridge (Optimized with Device Mapping)
================================================================

Преобразует нажатия пэдов Maschine Mikro MK3 в MIDI ноты.
Создаёт виртуальный MIDI порт в системе.
Поддерживает до 4 контроллеров одновременно!

✨ Новое:
- Постоянная привязка устройств по серийным номерам!
- Переключение октав (банков нот)

🎹 Октавные банки (независимые для каждого устройства):
- PAD_MODE: C1-D#2   (ноты 36-51)  - базовая октава
- KEYBOARD: E2-G3    (ноты 52-67)  - +16 полутонов
- CHORDS:   G#3-B4   (ноты 68-83)  - +32 полутона
- STEP:     C5-D#6   (ноты 84-99)  - +48 полутонов

🔄 Переключение банков:
- TODO: Encoder Click - циклическое переключение банков (отключено для производительности)
- TODO: PAD_MODE, KEYBOARD, CHORDS, STEP кнопки - требует декодирования HID протокола
- Сейчас: все устройства работают в базовой октаве (PAD_MODE)

Использование:
    python3 midi_bridge.py              # Использовать сохраненную конфигурацию
    python3 midi_bridge.py --setup      # Настроить порядок устройств
    python3 midi_bridge.py --show       # Показать текущую конфигурацию

Требует: pip install python-rtmidi
"""

import time
import sys
import signal
import threading
from pathlib import Path
from maschine import (
    setup_devices_with_config,
    PadEventType,
    Color,
    PAD_COUNT,
    BRIGHTNESS_BRIGHT,
    load_device_config,
    save_device_config,
    get_config_path,
    Screen,
)

try:
    import rtmidi
except ImportError:
    print("❌ Ошибка: rtmidi не установлен")
    print("\nУстановите:")
    print("  pip install python-rtmidi")
    sys.exit(1)

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


# MIDI Configuration
MIDI_PORT_NAME = "Maschine MK3 MIDI"
LOGO_PATH = Path(__file__).parent / "logo.png"
LOGO_THRESHOLD = 110
MAX_DEVICES = 4
VELOCITY_THRESHOLD = 5  # Минимальная velocity для отправки MIDI события

# Performance tuning
# LED feedback is now synchronous (direct device.set_pad_light calls)

# Visual feedback colors
# Note: Orange is visually brighter than pure Red (uses red+green LEDs)
# Try: ORANGE, MAGENTA, FUCHSIA, CYAN, BLUE for brighter colors
PAD_DEFAULT_COLOR = Color.ORANGE   # Default pad color (when not pressed)
PAD_ACTIVE_COLOR = Color.WHITE     # Pad color when pressed

# Alternative bright colors to try:
# PAD_DEFAULT_COLOR = Color.RED          # Pure red (dimmer)
# PAD_DEFAULT_COLOR = Color.MAGENTA      # Pink-red (bright!)
# PAD_DEFAULT_COLOR = Color.FUCHSIA      # Hot pink (very bright!)
# PAD_DEFAULT_COLOR = Color.CYAN         # Bright blue-green
# PAD_DEFAULT_COLOR = Color.BLUE         # Bright blue

# Pad to MIDI note mapping (base octave: C1-D#2, notes 36-51)
PAD_TO_NOTE = {
    12: 36, 13: 37, 14: 38, 15: 39,
    8: 40, 9: 41, 10: 42, 11: 43,
    4: 44, 5: 45, 6: 46, 7: 47,
    0: 48, 1: 49, 2: 50, 3: 51,
}

# Octave banks (button → offset from base notes)
OCTAVE_BANKS = {
    'PAD_MODE': 0,     # C1-D#2   (36-51)
    'KEYBOARD': 16,    # E2-G3    (52-67)
    'CHORDS': 32,      # G#3-B4   (68-83)
    'STEP': 48,        # C5-D#6   (84-99)
}

# Button LED indices (from debug_controller.py)
BUTTON_LED_MAP = {
    'PAD_MODE': 27,
    'KEYBOARD': 28,
    'CHORDS': 29,
    'STEP': 30,
}


def load_image_to_screen(image_path: str, threshold: int = 128) -> Screen:
    """
    Загрузить изображение и конвертировать в Screen

    Args:
        image_path: Путь к изображению
        threshold: Порог яркости для конвертации в ч/б (0-255)

    Returns:
        Screen объект с загруженным изображением
    """
    if not HAS_PIL:
        return None

    try:
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
                # Если пиксель светлее порога - включить
                if pixels[x, y] > threshold:
                    screen.set_pixel(x, y, on=True)

        return screen
    except Exception as e:
        print(f"⚠️  Не удалось загрузить логотип: {e}")
        return None


def display_logo_on_devices(devices):
    """Отобразить логотип на всех устройствах"""
    if not HAS_PIL:
        return

    if not LOGO_PATH.exists():
        return

    try:
        screen = load_image_to_screen(str(LOGO_PATH), LOGO_THRESHOLD)
        if screen:
            for device in devices:
                screen.write(device.device)
            print(f"✅ Логотип отображён на {len(devices)} устройствах")
    except Exception as e:
        print(f"⚠️  Ошибка отображения логотипа: {e}")


def show_config():
    """Показать текущую конфигурацию"""
    config = load_device_config()

    if not config:
        print("❌ Конфигурация не найдена")
        print(f"   Запустите: python3 {sys.argv[0]} --setup")
        return

    print("\n" + "=" * 60)
    print("📋 Текущая конфигурация устройств")
    print("=" * 60)
    print()

    # Sort by device number
    sorted_serials = sorted(config.items(), key=lambda x: x[1])

    for serial, device_num in sorted_serials:
        print(f"  Device {device_num} → Serial: {serial}")

    print()
    print(f"📁 Файл: {get_config_path()}")
    print()


def setup_device_mapping(devices):
    """Интерактивная настройка порядка устройств"""
    print("\n" + "=" * 60)
    print("🎹 Настройка порядка устройств")
    print("=" * 60)
    print()
    print(f"Найдено устройств: {len(devices)}")
    print()

    config = {}
    used_numbers = set()

    for i, device in enumerate(devices, 1):
        print(f"\n--- Устройство {i}/{len(devices)} ---")
        print(f"Serial: {device.serial}")

        # Light up device to identify it
        print("⚡ Подсвечиваю устройство...")

        # Flash pattern to identify
        for _ in range(3):
            device.set_all_pads(Color.CYAN, brightness=0x7f)
            time.sleep(0.3)
            device.clear()
            time.sleep(0.2)

        while True:
            try:
                num_str = input(f"\nКакой номер присвоить этому устройству? (1-{MAX_DEVICES}): ").strip()
                num = int(num_str)

                if num < 1 or num > MAX_DEVICES:
                    print(f"❌ Номер должен быть от 1 до {MAX_DEVICES}")
                    continue

                if num in used_numbers:
                    print(f"❌ Номер {num} уже используется!")
                    continue

                config[device.serial] = num
                used_numbers.add(num)
                print(f"✅ Устройство {device.serial} → Device {num}")
                break

            except ValueError:
                print("❌ Введите число!")
            except KeyboardInterrupt:
                print("\n\n🛑 Настройка отменена")
                return None

    # Show summary
    print("\n" + "=" * 60)
    print("📋 Итоговая конфигурация:")
    print("=" * 60)

    sorted_config = sorted(config.items(), key=lambda x: x[1])
    for serial, num in sorted_config:
        print(f"  Device {num} → {serial}")

    print("\n💾 Сохранить эту конфигурацию? (y/n): ", end='')

    try:
        answer = input().strip().lower()
        if answer in ['y', 'yes', 'д', 'да', '']:
            if save_device_config(config):
                return config
    except KeyboardInterrupt:
        print("\n\n🛑 Отменено")

    return None




class DeviceBridge:
    """MIDI bridge для одного устройства"""

    def __init__(self, device, device_num, midi_out):
        self.device = device
        self.device_num = device_num
        # MIDI channels: Device 1→Ch1, Device 2→Ch2, Device 3→Ch3, Device 4→Ch4
        # (MIDI protocol uses 0-based indexing: Ch1=0, Ch2=1, Ch3=2, Ch4=3)
        self.midi_channel = device_num - 1
        self.midi_out = midi_out
        self.active_notes = set()
        self.running = False
        self.thread = None

        # Octave bank state (independent per device)
        self.current_bank = 'PAD_MODE'  # Default bank
        self.octave_offset = OCTAVE_BANKS[self.current_bank]

    def start(self):
        """Запустить поток чтения"""
        self.running = True

        # Light up default bank button
        self._update_bank_leds()

        # Initialize all pads with default color (one-time operation)
        self.device.set_all_pads(PAD_DEFAULT_COLOR, brightness=BRIGHTNESS_BRIGHT)

        self.thread = threading.Thread(target=self._read_loop, daemon=True)
        self.thread.start()

    def set_octave_bank(self, bank_name):
        """
        Переключить октавный банк

        Args:
            bank_name: Имя банка ('PAD_MODE', 'KEYBOARD', 'CHORDS', 'STEP')
        """
        if bank_name not in OCTAVE_BANKS:
            return

        # Turn off all active notes before switching
        self.all_notes_off()

        # Update bank
        self.current_bank = bank_name
        self.octave_offset = OCTAVE_BANKS[bank_name]

        # Update button LEDs
        self._update_bank_leds()

        # Reset all pads to default color (visual feedback for bank change)
        self.device.set_all_pads(PAD_DEFAULT_COLOR, brightness=BRIGHTNESS_BRIGHT)

        # Log bank change
        offset_str = f"+{self.octave_offset}" if self.octave_offset > 0 else "±0"
        # print(f"🎹 D{self.device_num}: Bank → {bank_name} ({offset_str} semitones)")

    def _update_bank_leds(self):
        """Обновить подсветку кнопок банков"""
        with self.device.lock:
            # Turn off all bank button LEDs
            for _, led_idx in BUTTON_LED_MAP.items():
                self.device.led_buffer[1 + led_idx] = 0x00

            # Light up current bank button
            led_idx = BUTTON_LED_MAP.get(self.current_bank)

            if led_idx is not None:
                self.device.led_buffer[1 + led_idx] = 0x7f  # Max brightness

            # Single write for all changes
            try:
                self.device.device.write(self.device.led_buffer)
            except Exception:
                pass

    def stop(self):
        """Остановить поток чтения"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)

    def _read_loop(self):
        """
        Главный цикл чтения - raw HID с парсингом пэдов и кнопок

        Читает raw HID reports и парсит:
        - Report 0x01: Кнопки (для переключения октав)
        - Report 0x02: Пэды (для MIDI notes)
        """
        button_states = {}  # Track button states to detect presses (not holds)

        while self.running:
            # Read raw HID data
            try:
                data = self.device.device.read(64, timeout_ms=1)
            except Exception as e:
                print(f"❌ D{self.device_num}: HID read error: {e}")
                continue

            if not data or len(data) < 1:
                continue

            report_id = data[0]

            # ============================================================
            # Report 0x01: Button Events
            # ============================================================
            if report_id == 0x01:
                if len(data) < 5:
                    continue

                # Parse button bytes (bytes 1-4)
                # Button LEDs: PAD_MODE(27), KEYBOARD(28), CHORDS(29), STEP(30)
                # Button 27-30 are in byte 4 (contains buttons 24-31), bits 3-6

                button_byte = data[4]

                # Check bank buttons (using tuple for performance)
                # Format: (bank_name, button_idx, bit_mask)
                bank_checks = (
                    ('PAD_MODE', 27, button_byte & 0x08),  # bit 3
                    ('KEYBOARD', 28, button_byte & 0x10),  # bit 4
                    ('CHORDS', 29, button_byte & 0x20),    # bit 5
                    ('STEP', 30, button_byte & 0x40),      # bit 6
                )

                for bank_name, button_idx, is_pressed in bank_checks:
                    was_pressed = button_states.get(button_idx, False)
                    is_pressed = is_pressed != 0

                    # Detect rising edge (button just pressed, not held)
                    if is_pressed and not was_pressed:
                        self.set_octave_bank(bank_name)

                    button_states[button_idx] = is_pressed

            # ============================================================
            # Report 0x02: Pad Events
            # ============================================================
            elif report_id == 0x02:
                # Parse pad events (same as read_pads_with_velocity)
                for i in range(1, len(data), 3):
                    if i + 2 >= len(data):
                        break

                    pad_idx = data[i]
                    event_byte = data[i + 1]
                    velocity_low = data[i + 2]

                    # Check for end marker
                    if pad_idx == 0 and event_byte == 0:
                        break

                    event_type = event_byte & 0xf0

                    if not (0 <= pad_idx < PAD_COUNT):
                        continue

                    # Convert 12-bit velocity to 7-bit MIDI velocity
                    velocity_12bit = ((event_byte & 0x0f) << 8) | velocity_low
                    velocity = min(127, velocity_12bit >> 5)

                    base_note = PAD_TO_NOTE.get(pad_idx)
                    if base_note is None:
                        continue

                    # Apply octave offset
                    note = base_note + self.octave_offset

                    # Check for press events
                    if event_type == PadEventType.NOTE_ON:
                        if velocity < VELOCITY_THRESHOLD:
                            continue

                        self.send_note_on(note, velocity)

                        # Light up pad with active color (white)
                        self.device.set_pad_light(pad_idx, PAD_ACTIVE_COLOR, brightness=BRIGHTNESS_BRIGHT, on=True)

                    # Check for release events
                    elif event_type in [PadEventType.PRESS_OFF, PadEventType.NOTE_OFF]:
                        self.send_note_off(note)

                        # Return pad to default color (red)
                        self.device.set_pad_light(pad_idx, PAD_DEFAULT_COLOR, brightness=BRIGHTNESS_BRIGHT, on=True)

    def send_note_on(self, note, velocity):
        """Отправить MIDI Note On"""
        if self.midi_out and velocity > 0:
            message = [0x90 + self.midi_channel, note, velocity]
            self.midi_out.send_message(message)
            self.active_notes.add(note)

    def send_note_off(self, note):
        """Отправить MIDI Note Off"""
        if self.midi_out and note in self.active_notes:
            message = [0x80 + self.midi_channel, note, 0]
            self.midi_out.send_message(message)
            self.active_notes.discard(note)

    def all_notes_off(self):
        """Выключить все активные ноты"""
        for note in list(self.active_notes):
            self.send_note_off(note)

    @staticmethod
    def _note_to_name(note):
        """Конвертировать MIDI ноту в название"""
        notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        octave = (note // 12) - 1
        note_name = notes[note % 12]
        return f"{note_name}{octave}"


class MIDIBridge:
    """MIDI bridge координатор"""

    def __init__(self, devices, config=None):
        self.devices = devices
        self.config = config or {}
        self.midi_out = None
        self.running = False
        self.device_bridges = []

        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Обработчик Ctrl+C"""
        print("\n\n🛑 Остановка...")
        self.running = False

    def setup_midi(self):
        """Создать MIDI порт и device bridges"""
        try:
            self.midi_out = rtmidi.MidiOut()
            self.midi_out.open_virtual_port(MIDI_PORT_NAME)

            print(f"✅ MIDI порт: '{MIDI_PORT_NAME}'")
            print(f"   LED feedback: Synchronous (direct writes)")
            print()

            # Sort devices by config
            sorted_devices = []

            if self.config:
                # Use configured order
                for device in self.devices:
                    device_num = self.config.get(device.serial)
                    if device_num:
                        sorted_devices.append((device, device_num))

                # Sort by device number
                sorted_devices.sort(key=lambda x: x[1])

                print("📋 Используется сохраненная конфигурация:")
                for device, num in sorted_devices:
                    print(f"   Device {num} [{device.serial}] → MIDI Ch{num}")
            else:
                # No config, use discovery order
                print("⚠️  Конфигурация не найдена, используется порядок обнаружения:")
                for i, device in enumerate(self.devices, 1):
                    sorted_devices.append((device, i))
                    print(f"   Device {i} [{device.serial}] → MIDI Ch{i}")

                print(f"\n💡 Совет: запустите `python3 {sys.argv[0]} --setup` для постоянной привязки")

            # Create bridges
            for device, device_num in sorted_devices:
                bridge = DeviceBridge(device, device_num, self.midi_out)
                self.device_bridges.append(bridge)

            return True

        except Exception as e:
            print(f"❌ Ошибка MIDI: {e}")
            return False

    def run(self):
        """Главный цикл"""
        self.running = True

        print("\n🎹 MIDI Bridge (Optimized)")
        print("=" * 60)
        print(f"Устройств: {len(self.device_bridges)}")
        print(f"Velocity threshold: {VELOCITY_THRESHOLD}")
        print(f"LED feedback: Synchronous")
        print("=" * 60)
        print()

        print("⚡ Запуск потоков...")
        for bridge in self.device_bridges:
            bridge.start()
        print("✅ Работаю!\n")

        try:
            while self.running:
                time.sleep(0.1)

        finally:
            print("\n🛑 Остановка...")
            for bridge in self.device_bridges:
                bridge.stop()

            print("\n   Очистка...")
            for bridge in self.device_bridges:
                bridge.all_notes_off()
                bridge.device.clear()

            if self.midi_out:
                self.midi_out.close_port()

            print("✅ Завершено")


def main():
    # Parse arguments
    if '--show' in sys.argv:
        show_config()
        return

    setup_mode = '--setup' in sys.argv

    print("=" * 60)
    print("🎹 Maschine MK3 → MIDI Bridge")
    print("=" * 60)
    print()

    # Setup devices with configuration and visual identification
    # Show device numbers on pads with reduced duration (0.5s)
    sorted_devices = setup_devices_with_config(
        max_count=MAX_DEVICES,
        show_numbers=True,
        show_duration=0.5
    )

    if not sorted_devices:
        print("❌ Устройства не найдены")
        print("\n1. Подключите Maschine Mikro MK3")
        print("2. killall NIHardwareAgent")
        return

    # Extract devices and build config from sorted_devices
    devices = []
    config = {}
    for device, device_num in sorted_devices:
        devices.append(device)
        config[device.serial] = device_num

    print(f"✅ Найдено: {len(devices)} устройств")
    for device, device_num in sorted_devices:
        print(f"   Device {device_num}: {device.serial}")
    print()

    # Display logo on all devices
    display_logo_on_devices(devices)
    print()

    # Setup mode: allow user to reconfigure
    if setup_mode:
        new_config = setup_device_mapping(devices)
        if not new_config:
            print("❌ Настройка не завершена")
            for device in devices:
                device.close()
            return
        config = new_config

    bridge = MIDIBridge(devices, config)

    if not bridge.setup_midi():
        for device in devices:
            device.close()
        return

    try:
        bridge.run()
    finally:
        for device in devices:
            device.close()
        print("✅ Закрыто\n")


if __name__ == "__main__":
    main()
