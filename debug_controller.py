#!/usr/bin/env python3
"""
🔍 Maschine Mikro MK3 - Full Controller Debugger
================================================

Утилита для отладки ВСЕХ элементов контроллера:
- Все кнопки (encoder, transport, group buttons)
- Все LED (pads, buttons, sliders)
- MIDI обратная связь из DAW

Использование:
    python3 debug_controller.py                # Дебаг всех элементов
    python3 debug_controller.py --buttons      # Только кнопки
    python3 debug_controller.py --leds         # Только LED
    python3 debug_controller.py --midi-in      # MIDI обратная связь из DAW
"""

import time
import sys
import threading
from maschine import find_devices, Color, BRIGHTNESS_BRIGHT

try:
    import rtmidi
    HAS_RTMIDI = True
except ImportError:
    HAS_RTMIDI = False
    print("⚠️  rtmidi не установлен - MIDI обратная связь недоступна")
    print("   Установите: pip install python-rtmidi\n")


# ============================================================================
# LED Layout Constants
# ============================================================================

# Button LED offsets (from maschine-mikro-mk3-driver/crates/maschine_library/src/controls.rs)
BUTTON_LED_MAP = {
    # Top row
    'MASCHINE': 0,
    'STAR': 1,
    'BROWSE': 2,
    'VOLUME': 3,

    # Second row
    'SWING': 4,
    'TEMPO': 5,
    'PLUGIN': 6,
    'SAMPLING': 7,

    # Third row
    'LEFT': 8,
    'RIGHT': 9,
    'PITCH': 10,
    'MOD': 11,

    # Fourth row
    'PERFORM': 12,
    'NOTES': 13,
    'GROUP': 14,
    'AUTO': 15,

    # Fifth row
    'LOCK': 16,
    'NOTE_REPEAT': 17,
    'RESTART': 18,
    'ERASE': 19,

    # Sixth row
    'TAP': 20,
    'FOLLOW': 21,
    'PLAY': 22,
    'REC': 23,

    # Seventh row
    'STOP': 24,
    'SHIFT': 25,
    'FIXED_VEL': 26,
    'PAD_MODE': 27,

    # Eighth row
    'KEYBOARD': 28,
    'CHORDS': 29,
    'STEP': 30,
    'SCENE': 31,

    # Ninth row
    'PATTERN': 32,
    'EVENTS': 33,
    'VARIATION': 34,
    'DUPLICATE': 35,

    # Tenth row
    'SELECT': 36,
    'SOLO': 37,
    'MUTE': 38,

    # Note: EncoderPress (39) and EncoderTouch (40) don't have lights
}

# HID Button event indices (from HID reports)
BUTTON_HID_MAP = {
    # These are example mappings - actual values may differ
    # Will be discovered during debug session
    0x50: 'RESTART',
    0x51: 'LOOP',
    0x52: 'ERASE',
    0x53: 'TAP',
    0x54: 'FOLLOW',
    0x55: 'PLAY',
    0x56: 'REC',
    0x57: 'STOP',
    0x58: 'GROUP_A',
    0x59: 'GROUP_B',
    0x5A: 'GROUP_C',
    0x5B: 'GROUP_D',
    0x5C: 'GROUP_E',
    0x5D: 'GROUP_F',
    0x5E: 'GROUP_G',
    0x5F: 'GROUP_H',
}


# ============================================================================
# LED Test Functions
# ============================================================================

def test_all_button_leds(device):
    """Тест всех LED кнопок"""
    print("\n" + "="*70)
    print("🔆 ТЕСТ ВСЕХ BUTTON LED")
    print("="*70)
    print("\nПоследовательно зажигаем каждую кнопку...")
    print("(Основано на Rust драйвере maschine-mikro-mk3-driver)")
    print()

    for button_name, led_offset in sorted(BUTTON_LED_MAP.items(), key=lambda x: x[1]):
        print(f"  [{led_offset:2d}] {button_name:20s} ", end="", flush=True)

        # Set LED on - button LEDs use direct brightness value (0x00-0x7f)
        with device.lock:
            # LED buffer structure: [0x80 report_id] + [80 bytes status]
            # Button LEDs are at indices 0-38 in status array
            # Which corresponds to led_buffer[1+led_offset] after report_id
            device.led_buffer[1 + led_offset] = 0x7f  # Max brightness (Brightness::Bright)
            try:
                device.device.write(device.led_buffer)
            except:
                pass

        time.sleep(0.3)

        # Set LED off
        with device.lock:
            device.led_buffer[1 + led_offset] = 0x00
            try:
                device.device.write(device.led_buffer)
            except:
                pass

        print("✓")
        time.sleep(0.1)

    print("\n✅ Тест button LED завершён")


def test_pad_leds_rainbow(device):
    """Тест пэдов - радужный паттерн"""
    print("\n" + "="*70)
    print("🌈 ТЕСТ PAD LED - РАДУГА")
    print("="*70)
    print()

    colors = [
        ('Red', Color.RED),
        ('Orange', Color.ORANGE),
        ('Yellow', Color.YELLOW),
        ('Green', Color.GREEN),
        ('Cyan', Color.CYAN),
        ('Blue', Color.BLUE),
        ('Violet', Color.VIOLET),
        ('Magenta', Color.MAGENTA),
    ]

    print("Переливающаяся радуга на пэдах...")

    try:
        for _ in range(10):  # 10 циклов
            for color_name, color_idx in colors:
                device.set_all_pads(color_idx, BRIGHTNESS_BRIGHT)
                time.sleep(0.2)
    except KeyboardInterrupt:
        pass

    device.clear()
    print("\n✅ Тест pad LED завершён")


def test_led_brightness_levels(device):
    """Тест уровней яркости"""
    print("\n" + "="*70)
    print("💡 ТЕСТ УРОВНЕЙ ЯРКОСТИ")
    print("="*70)
    print()

    brightness_levels = [
        ('Off', 0x00),
        ('Dim', 0x2a),
        ('Normal', 0x55),
        ('Bright', 0x7f),
    ]

    print("Тестируем яркость на пэдах...")

    for level_name, brightness in brightness_levels:
        print(f"  {level_name:10s} (0x{brightness:02x})")
        device.set_all_pads(Color.BLUE, brightness)
        time.sleep(1.5)

    device.clear()
    print("\n✅ Тест яркости завершён")


# ============================================================================
# Button Debug Functions
# ============================================================================

def debug_all_buttons(device):
    """Отладка всех кнопок - показывает HID события"""
    print("\n" + "="*70)
    print("🔘 ДЕБАГ ВСЕХ КНОПОК И ЭНКОДЕРА")
    print("="*70)
    print("\nНажимайте любые кнопки на контроллере...")
    print("Будут показаны все HID события (Report ID 0x01)")
    print()
    print("Формат HID Report 0x01:")
    print("  [1-4] = Button states")
    print("  [5]   = Encoder Press (0x80 when pressed)")
    print("  [6]   = Encoder Touch (0x01 when touched)")
    print("  [7]   = Encoder Position (0-15 absolute)")
    print("  [8-9] = Constants")
    print()
    print("Нажмите Ctrl+C для остановки\n")

    last_encoder_pos = None

    try:
        while True:
            # Read button events (Report ID 0x01)
            data = device.device.read(64, timeout_ms=10)

            if data and data[0] == 0x01:
                # Check if anything interesting happened
                has_button = any(data[i] != 0 for i in range(1, 5))
                encoder_press = data[5] if len(data) > 5 else 0
                encoder_touch = data[6] if len(data) > 6 else 0
                encoder_pos = data[7] if len(data) > 7 else 0

                # Only print if something changed
                if has_button or encoder_press == 0x80 or (encoder_touch == 0x01 and encoder_pos != last_encoder_pos):
                    # Button event
                    print(f"📥 HID Report 0x01: ", end="")

                    # Show relevant bytes
                    for i in range(min(10, len(data))):
                        if data[i] != 0:
                            print(f"[{i:2d}]=0x{data[i]:02x} ", end="")

                    # Decode encoder
                    if encoder_press == 0x80:
                        print(" → 🔘 ENCODER PRESS", end="")
                    elif encoder_touch == 0x01:
                        if last_encoder_pos is not None and encoder_pos != last_encoder_pos:
                            delta = encoder_pos - last_encoder_pos
                            if delta > 8:
                                delta -= 16
                            elif delta < -8:
                                delta += 16
                            direction = "↻CW" if delta > 0 else "↺CCW"
                            print(f" → 🎚️  ENCODER {direction} pos={encoder_pos}", end="")
                        else:
                            print(f" → 👆 ENCODER TOUCH pos={encoder_pos}", end="")

                    # Try to identify button from bytes 1-4
                    if has_button:
                        print(f" → 🔘 BUTTON", end="")

                    print()

                    last_encoder_pos = encoder_pos if encoder_touch == 0x01 else None

    except KeyboardInterrupt:
        print("\n\n✅ Дебаг кнопок завершён")


def debug_encoder(device):
    """Отладка энкодера"""
    print("\n" + "="*70)
    print("🎚️  ДЕБАГ ЭНКОДЕРА")
    print("="*70)
    print("\nИнформация об энкодере:")
    print("  • data[5] = Encoder Press (0x80 when pressed)")
    print("  • data[6] = Encoder Touch (0x01 when touched)")
    print("  • data[7] = Encoder Position (0-15 циклически)")
    print()
    print("Вращайте энкодер, касайтесь, нажимайте...")
    print("Нажмите Ctrl+C для остановки\n")

    last_position = None

    try:
        while True:
            data = device.device.read(64, timeout_ms=10)

            if data and data[0] == 0x01 and len(data) > 9:
                encoder_press = data[5] if len(data) > 5 else 0
                encoder_touch = data[6] if len(data) > 6 else 0
                encoder_position = data[7] if len(data) > 7 else 0

                # Detect encoder press
                if encoder_press == 0x80:
                    print(f"🔘 Encoder PRESS")
                    # Flash all pads white
                    device.set_all_pads(Color.WHITE, 0x7f)
                    time.sleep(0.1)
                    device.clear()

                # Detect encoder touch
                if encoder_touch == 0x01 and encoder_press != 0x80:
                    # Only show if just touched (no press)
                    if last_position is None:
                        print(f"👆 Encoder TOUCH")

                # Detect encoder rotation
                if encoder_touch == 0x01:
                    if last_position is not None and last_position != encoder_position:
                        # Calculate delta (циклически 0-15)
                        delta = encoder_position - last_position

                        # Handle wrap around
                        if delta > 8:
                            delta -= 16
                        elif delta < -8:
                            delta += 16

                        if delta > 0:
                            direction = "↻ CW"
                            color = Color.GREEN
                            pad = 15
                        else:
                            direction = "↺ CCW"
                            color = Color.BLUE
                            pad = 0
                            delta = abs(delta)

                        print(f"🎚️  Encoder: {direction} pos={encoder_position:2d} delta={delta:+2d}")

                        # Visual feedback
                        device.set_pad_light(pad, color, on=True)
                        time.sleep(0.05)
                        device.set_pad_light(pad, Color.OFF, on=False)

                    last_position = encoder_position
                else:
                    # Not touching - reset
                    if last_position is not None and encoder_touch == 0x00:
                        print(f"🖐️  Encoder RELEASE\n")
                    last_position = None

    except KeyboardInterrupt:
        print("\n\n✅ Дебаг энкодера завершён")
        device.clear()


# ============================================================================
# MIDI Feedback (DAW → Controller)
# ============================================================================

class MIDIFeedbackHandler:
    """Обработчик MIDI сообщений из DAW для управления контроллером"""

    def __init__(self, device):
        self.device = device
        self.running = False
        self.midi_in = None

    def start(self):
        """Запустить MIDI input"""
        if not HAS_RTMIDI:
            print("❌ rtmidi не установлен")
            return False

        try:
            self.midi_in = rtmidi.MidiIn()

            # List available MIDI ports
            ports = self.midi_in.get_ports()

            if not ports:
                print("❌ Нет доступных MIDI портов")
                return False

            print("\n" + "="*70)
            print("🎹 ДОСТУПНЫЕ MIDI ПОРТЫ:")
            print("="*70)
            for i, port_name in enumerate(ports):
                print(f"  [{i}] {port_name}")
            print()

            # Ask user to select port
            while True:
                try:
                    port_idx = input("Выберите порт (номер) или Enter для создания виртуального: ").strip()

                    if not port_idx:
                        # Create virtual port
                        self.midi_in.open_virtual_port("Maschine MK3 Feedback")
                        print("✅ Создан виртуальный MIDI порт: 'Maschine MK3 Feedback'")
                        break

                    port_idx = int(port_idx)
                    if 0 <= port_idx < len(ports):
                        self.midi_in.open_port(port_idx)
                        print(f"✅ Подключено к: {ports[port_idx]}")
                        break
                    else:
                        print("❌ Неверный номер порта")
                except ValueError:
                    print("❌ Введите число")
                except KeyboardInterrupt:
                    print("\n❌ Отменено")
                    return False

            # Set callback
            self.midi_in.set_callback(self._midi_callback)
            self.running = True

            print("\n" + "="*70)
            print("🎹 MIDI FEEDBACK ACTIVE")
            print("="*70)
            print("\nПротокол управления из DAW:")
            print("  • Note On (Ch1):  Control Pad LED")
            print("    - Note 36-51 → Pads 0-15")
            print("    - Velocity 0-127 → Color (0=OFF)")
            print()
            print("  • Control Change (Ch1): Control Button LED")
            print("    - CC 0-38 → Button LED 0-38")
            print("    - Value 0-127 → Brightness")
            print()
            print("Примеры:")
            print("  • Note On C2 (36) vel=8   → Pad 0 RED")
            print("  • Note On D2 (38) vel=56  → Pad 2 GREEN")
            print("  • Note On E2 (40) vel=0   → Pad 4 OFF")
            print("  • CC 22 value=127         → Button PLAY ON")
            print("  • CC 23 value=127         → Button REC ON")
            print("  • CC 24 value=0           → Button STOP OFF")
            print("="*70)

            return True

        except Exception as e:
            print(f"❌ Ошибка MIDI: {e}")
            return False

    def _midi_callback(self, event, data=None):
        """Обработка входящих MIDI сообщений"""
        message, deltatime = event

        if not message:
            return

        status = message[0]

        # Note On/Off (0x90-0x9F for channel 1-16)
        if status >= 0x90 and status <= 0x9F:
            channel = (status & 0x0F) + 1
            note = message[1] if len(message) > 1 else 0
            velocity = message[2] if len(message) > 2 else 0

            # Map MIDI note to pad (36-51 → pads 0-15)
            if 36 <= note <= 51:
                pad_idx = note - 36

                if velocity == 0:
                    # Note Off or velocity 0
                    self.device.set_pad_light(pad_idx, Color.OFF, on=False)
                    print(f"🎹 MIDI: Ch{channel} Note Off {note:3d} → Pad {pad_idx:2d} OFF")
                else:
                    # Note On - map velocity to color
                    color_idx = min(17, max(1, velocity // 8))  # 0-127 → 1-17
                    self.device.set_pad_light(pad_idx, color_idx, on=True)
                    print(f"🎹 MIDI: Ch{channel} Note On  {note:3d} vel={velocity:3d} → Pad {pad_idx:2d} Color={color_idx}")

        # Control Change (0xB0-0xBF)
        elif status >= 0xB0 and status <= 0xBF:
            channel = (status & 0x0F) + 1
            cc_num = message[1] if len(message) > 1 else 0
            cc_value = message[2] if len(message) > 2 else 0

            # Map CC to button LED (CC 0-38 → LED 0-38)
            if 0 <= cc_num <= 38:
                button_name = None
                for name, offset in BUTTON_LED_MAP.items():
                    if offset == cc_num:
                        button_name = name
                        break

                with self.device.lock:
                    # Button LEDs are at led_buffer[1 + offset] (after 0x80 report ID)
                    self.device.led_buffer[1 + cc_num] = cc_value
                    try:
                        self.device.device.write(self.device.led_buffer)
                    except:
                        pass

                button_info = f" ({button_name})" if button_name else ""
                print(f"🎹 MIDI: Ch{channel} CC{cc_num:3d}={cc_value:3d} → Button LED {cc_num}{button_info}")

    def stop(self):
        """Остановить MIDI input"""
        self.running = False
        if self.midi_in:
            self.midi_in.close_port()


# ============================================================================
# Interactive Menu
# ============================================================================

def show_menu():
    """Показать интерактивное меню"""
    print("\n" + "="*70)
    print("🔍 MASCHINE MIKRO MK3 - CONTROLLER DEBUGGER")
    print("="*70)
    print()
    print("Выберите режим:")
    print()
    print("  1. Тест всех Button LED")
    print("  2. Тест Pad LED (радуга)")
    print("  3. Тест уровней яркости")
    print("  4. Дебаг всех кнопок (HID события)")
    print("  5. Дебаг энкодера")
    print("  6. MIDI обратная связь (DAW → Controller)")
    print("  7. Полный тест (всё подряд)")
    print()
    print("  0. Выход")
    print()
    print("="*70)


def full_test_sequence(device):
    """Полная последовательность тестов"""
    print("\n🚀 ЗАПУСК ПОЛНОГО ТЕСТА...\n")

    test_all_button_leds(device)
    time.sleep(1)

    test_pad_leds_rainbow(device)
    time.sleep(1)

    test_led_brightness_levels(device)

    print("\n✅ Полный тест завершён!")


# ============================================================================
# Main
# ============================================================================

def main():
    # Parse arguments
    buttons_only = '--buttons' in sys.argv
    leds_only = '--leds' in sys.argv
    midi_in_only = '--midi-in' in sys.argv

    print("="*70)
    print("🔍 Maschine Mikro MK3 - Full Controller Debugger")
    print("="*70)
    print()

    # Find device
    devices = find_devices(max_count=1)

    if not devices:
        print("❌ Устройство не найдено")
        print("\n1. Подключите Maschine Mikro MK3")
        print("2. killall NIHardwareAgent")
        return

    device = devices[0]
    print(f"✅ Подключено: {device.serial}\n")

    try:
        # Command-line mode
        if buttons_only:
            debug_all_buttons(device)
        elif leds_only:
            full_test_sequence(device)
        elif midi_in_only:
            if HAS_RTMIDI:
                handler = MIDIFeedbackHandler(device)
                if handler.start():
                    print("\n⚡ MIDI Feedback активен. Нажмите Ctrl+C для остановки...\n")
                    try:
                        while True:
                            time.sleep(0.1)
                    except KeyboardInterrupt:
                        print("\n\n🛑 Остановка...")
                        handler.stop()
            else:
                print("❌ rtmidi не установлен")
        else:
            # Interactive menu
            while True:
                show_menu()

                try:
                    choice = input("Ваш выбор: ").strip()

                    if choice == '0':
                        break
                    elif choice == '1':
                        test_all_button_leds(device)
                    elif choice == '2':
                        test_pad_leds_rainbow(device)
                    elif choice == '3':
                        test_led_brightness_levels(device)
                    elif choice == '4':
                        debug_all_buttons(device)
                    elif choice == '5':
                        debug_encoder(device)
                    elif choice == '6':
                        if HAS_RTMIDI:
                            handler = MIDIFeedbackHandler(device)
                            if handler.start():
                                try:
                                    while True:
                                        time.sleep(0.1)
                                except KeyboardInterrupt:
                                    print("\n\n🛑 Остановка...")
                                    handler.stop()
                        else:
                            print("❌ rtmidi не установлен")
                    elif choice == '7':
                        full_test_sequence(device)
                    else:
                        print("❌ Неверный выбор")

                except KeyboardInterrupt:
                    print("\n")
                    break

    finally:
        print("\nОчистка...")
        device.clear()
        device.close()
        print("✅ Готово\n")


if __name__ == "__main__":
    main()

