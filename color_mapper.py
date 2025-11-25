#!/usr/bin/env python3
"""
🎨 COLOR MAPPER - Определение правильных цветов палитры
=====================================================

Программа зажигает все 16 пэдов разными цветами (индексы 1-16)
и показывает уже известный маппинг.
"""

import hid
import time
import os

VENDOR_ID = 0x17cc
PRODUCT_ID = 0x1700

LED_REPORT_ID = 0x80
LED_BUFFER_SIZE = 81
PAD_LED_OFFSET = 40
BRIGHTNESS_BRIGHT = 0x7f

# Правильная палитра из драйвера MK3 (lights.rs)
PALETTE = {
    0: "Off",
    1: "Red",
    2: "Orange",
    3: "Light Orange",
    4: "Warm Yellow",
    5: "Yellow",
    6: "Lime",
    7: "Green",
    8: "Mint",
    9: "Cyan",
    10: "Turquoise",
    11: "Blue",
    12: "Plum",
    13: "Violet",
    14: "Purple",
    15: "Magenta",
    16: "Fuchsia",
    17: "White",
}


class MaschineDevice:
    def __init__(self, serial):
        self.serial = serial
        self.device = hid.device()
        self.device.open(VENDOR_ID, PRODUCT_ID, serial)

        # NHL handshake
        client_id = os.urandom(8)
        self.device.write([0x03, 0x01] + list(client_id) + [0x00] * 54)
        time.sleep(0.05)

        # Wake-up sequences
        for seq in [
            [0x01, 0x00, 0x00, 0x02, 0x01, 0x00, 0x00, 0x00] + [0x00] * 56,
            [0x04, 0x00, 0x01, 0x00, 0x00, 0x00] + [0x00] * 58,
            [0x80, 0x00] + [0x00] * 62,
        ]:
            self.device.write(seq)
            time.sleep(0.03)

        self.device.set_nonblocking(True)
        time.sleep(0.1)

        self.led_buffer = bytearray(LED_BUFFER_SIZE)
        self.led_buffer[0] = LED_REPORT_ID
        self.clear()

    def set_pad_light(self, pad_index, color_index):
        if not (0 <= pad_index <= 15):
            return

        if color_index > 0:
            value = (color_index << 2) | (BRIGHTNESS_BRIGHT & 0b11)
        else:
            value = 0

        self.led_buffer[PAD_LED_OFFSET + pad_index] = value
        self.device.write(self.led_buffer)

    def clear(self):
        for i in range(16):
            self.led_buffer[PAD_LED_OFFSET + i] = 0
        self.device.write(self.led_buffer)

    def close(self):
        self.clear()
        self.device.close()


def main():
    print("=" * 70)
    print("🎨 COLOR MAPPER - Определение цветов палитры")
    print("=" * 70)
    print()

    # Find first device
    all_serials = []
    for device_dict in hid.enumerate(VENDOR_ID, PRODUCT_ID):
        serial = device_dict.get('serial_number')
        if serial and serial not in all_serials:
            all_serials.append(serial)

    if len(all_serials) == 0:
        print("❌ Устройство не найдено")
        return

    print(f"✓ Найдено {len(all_serials)} устройств")
    print("Используем первое устройство")
    print()

    device = MaschineDevice(all_serials[0])

    print("=" * 70)
    print("ПРОСМОТР ПАЛИТРЫ ЦВЕТОВ MK3")
    print("=" * 70)
    print()
    print("Полная палитра из драйвера (18 цветов, индексы 0-17):")
    print()
    for idx, name in PALETTE.items():
        if idx == 0:
            print(f"   {idx:2} | {name:16} | (выключен)")
        else:
            print(f"   {idx:2} | {name:16} |")
    print()
    print("Сейчас я зажгу все 16 пэдов цветами 1-16 (без Off и White).")
    print()
    input("Нажми Enter чтобы посмотреть палитру...")
    print()

    # Зажигаем все 16 пэдов цветами 1-16
    for pad_idx in range(16):
        color_idx = pad_idx + 1  # Цвета 1-16
        device.set_pad_light(pad_idx, color_idx)

    print("✓ Все пэды зажжены!")
    print()
    print("=" * 70)
    print("МАППИНГ: ПЭД → ПАЛИТРА → ЦВЕТ")
    print("=" * 70)
    print()
    print("Физическая раскладка пэдов (вид сверху):")
    print()
    print("  12  13  14  15    (верхний ряд)")
    print("   8   9  10  11")
    print("   4   5   6   7")
    print("   0   1   2   3    (нижний ряд)")
    print()

    # Показываем маппинг
    for pad_idx in range(16):
        color_palette_idx = pad_idx + 1
        color_name = PALETTE.get(color_palette_idx, "?")
        print(f"  Пэд {pad_idx:2} → Палитра #{color_palette_idx:2} → {color_name}")

    print()
    input("Нажми Enter чтобы продолжить...")

    color_map = dict(PALETTE)

    # Показываем результат
    print("\n" + "=" * 70)
    print("ПОЛНАЯ ПАЛИТРА MK3")
    print("=" * 70)
    print()

    for idx, color in sorted(PALETTE.items()):
        if idx == 0:
            print(f"  {idx:2} | {color:16} | (выключен)")
        else:
            print(f"  {idx:2} | {color:16} |")

    print()
    print("=" * 70)
    print("РЕКОМЕНДАЦИИ ДЛЯ ИГР (контрастные цвета)")
    print("=" * 70)
    print()
    print("Хорошо различимые цвета:")
    print("   1 = Red (красный)")
    print("   5 = Yellow (жёлтый)")
    print("   7 = Green (зелёный)")
    print("   9 = Cyan (бирюзовый)")
    print("  11 = Blue (синий)")
    print("  14 = Purple (пурпурный)")
    print("  15 = Magenta (маджента)")
    print()
    print("Пример для игры (6 цветов):")
    print("CARD_COLORS = [1, 5, 7, 9, 11, 15]")
    print()

    device.close()
    print("✅ Готово!")


if __name__ == "__main__":
    main()

