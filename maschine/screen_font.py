#!/usr/bin/env python3
"""
Maschine Mikro MK3 Screen Font
==============================

Встроенный шрифт для отображения цифр и базовых символов на экране.
Основан на font.rs из оригинального драйвера.
"""

# Шрифт для цифр (8x8 пикселей)
DIGIT_FONT = {
    0: [
        b"   xxx  ",
        b"  x   x ",
        b" x     x",
        b" x     x",
        b" x     x",
        b" x     x",
        b"  x   x ",
        b"   xxx  ",
    ],
    1: [
        b"     xx ",
        b"     xx ",
        b"    x x ",
        b"  xx  x ",
        b"      x ",
        b"      x ",
        b"      x ",
        b"  xxxxxx",
    ],
    2: [
        b"   xxxx ",
        b" x     x",
        b" x     x",
        b"      x ",
        b"    x   ",
        b"  x     ",
        b" x      ",
        b" xxxxxxx",
    ],
    3: [
        b"  xxxxx ",
        b" x     x",
        b"      x ",
        b"   xxxx ",
        b"       x",
        b"       x",
        b" x    x ",
        b"  xxxx  ",
    ],
    4: [
        b" x     x",
        b" x     x",
        b" x     x",
        b" x    xx",
        b"  xxxx x",
        b"       x",
        b"       x",
        b"       x",
    ],
    5: [
        b" xxxxxxx",
        b" x      ",
        b" x      ",
        b" xxxxxx ",
        b"       x",
        b"       x",
        b"       x",
        b" xxxxxx ",
    ],
    6: [
        b"  xxxxx ",
        b" x     x",
        b" x      ",
        b" x xxx  ",
        b" xx   xx",
        b" x     x",
        b" x     x",
        b"  xxxxx ",
    ],
    7: [
        b" xxxxxxx",
        b"       x",
        b"       x",
        b"      x ",
        b"     x  ",
        b"    x   ",
        b"   x    ",
        b"  x     ",
    ],
    8: [
        b"  xxxxx ",
        b" x     x",
        b" x     x",
        b"  xxxxx ",
        b" x     x",
        b" x     x",
        b" x     x",
        b"  xxxxx ",
    ],
    9: [
        b"  xxxxx ",
        b" x     x",
        b" x     x",
        b" x     x",
        b"  xxxxxx",
        b"       x",
        b" x     x",
        b"  xxxxx ",
    ],
}


def draw_digit(screen, x: int, y: int, digit: int, scale: int = 1):
    """
    Нарисовать цифру на экране

    Args:
        screen: Объект Screen
        x: X координата (левый верхний угол)
        y: Y координата (левый верхний угол)
        digit: Цифра 0-9
        scale: Масштаб (1 = 8x8, 2 = 16x16, и т.д.)
    """
    if digit not in DIGIT_FONT:
        return

    bitmap = DIGIT_FONT[digit]

    for i in range(8 * scale):
        for j in range(8 * scale):
            src_i = i // scale
            src_j = j // scale

            if src_i < len(bitmap) and src_j < len(bitmap[src_i]):
                pixel = bitmap[src_i][src_j] != ord(b' ')
                if pixel:
                    screen.set_pixel(x + j, y + i, on=True)


# Шрифт для букв (5x7 пикселей, более компактный)
LETTER_FONT = {
    'A': [
        b" xxx ",
        b"x   x",
        b"x   x",
        b"xxxxx",
        b"x   x",
        b"x   x",
        b"x   x",
    ],
    'B': [
        b"xxxx ",
        b"x   x",
        b"x   x",
        b"xxxx ",
        b"x   x",
        b"x   x",
        b"xxxx ",
    ],
    'C': [
        b" xxxx",
        b"x    ",
        b"x    ",
        b"x    ",
        b"x    ",
        b"x    ",
        b" xxxx",
    ],
    'D': [
        b"xxxx ",
        b"x   x",
        b"x   x",
        b"x   x",
        b"x   x",
        b"x   x",
        b"xxxx ",
    ],
    'E': [
        b"xxxxx",
        b"x    ",
        b"x    ",
        b"xxxx ",
        b"x    ",
        b"x    ",
        b"xxxxx",
    ],
    'F': [
        b"xxxxx",
        b"x    ",
        b"x    ",
        b"xxxx ",
        b"x    ",
        b"x    ",
        b"x    ",
    ],
    'G': [
        b" xxxx",
        b"x    ",
        b"x    ",
        b"x  xx",
        b"x   x",
        b"x   x",
        b" xxxx",
    ],
    'H': [
        b"x   x",
        b"x   x",
        b"x   x",
        b"xxxxx",
        b"x   x",
        b"x   x",
        b"x   x",
    ],
    'I': [
        b"xxxxx",
        b"  x  ",
        b"  x  ",
        b"  x  ",
        b"  x  ",
        b"  x  ",
        b"xxxxx",
    ],
    'O': [
        b" xxx ",
        b"x   x",
        b"x   x",
        b"x   x",
        b"x   x",
        b"x   x",
        b" xxx ",
    ],
    'P': [
        b"xxxx ",
        b"x   x",
        b"x   x",
        b"xxxx ",
        b"x    ",
        b"x    ",
        b"x    ",
    ],
    'S': [
        b" xxxx",
        b"x    ",
        b"x    ",
        b" xxx ",
        b"    x",
        b"    x",
        b"xxxx ",
    ],
    'T': [
        b"xxxxx",
        b"  x  ",
        b"  x  ",
        b"  x  ",
        b"  x  ",
        b"  x  ",
        b"  x  ",
    ],
    ' ': [
        b"     ",
        b"     ",
        b"     ",
        b"     ",
        b"     ",
        b"     ",
        b"     ",
    ],
    ':': [
        b"     ",
        b"  x  ",
        b"  x  ",
        b"     ",
        b"  x  ",
        b"  x  ",
        b"     ",
    ],
    '-': [
        b"     ",
        b"     ",
        b"     ",
        b"xxxxx",
        b"     ",
        b"     ",
        b"     ",
    ],
}


def draw_text_5x7(screen, x: int, y: int, text: str, scale: int = 1):
    """
    Нарисовать текст шрифтом 5x7

    Args:
        screen: Объект Screen
        x: X координата (левый верхний угол)
        y: Y координата (левый верхний угол)
        text: Текст для отрисовки (заглавные буквы и цифры)
        scale: Масштаб
    """
    cursor_x = x

    for char in text.upper():
        if char in LETTER_FONT:
            bitmap = LETTER_FONT[char]

            for i in range(7 * scale):
                for j in range(5 * scale):
                    src_i = i // scale
                    src_j = j // scale

                    if src_i < len(bitmap) and src_j < len(bitmap[src_i]):
                        pixel = bitmap[src_i][src_j] != ord(b' ')
                        if pixel:
                            screen.set_pixel(cursor_x + j, y + i, on=True)

            cursor_x += 5 * scale + scale  # Ширина символа + отступ
        elif char.isdigit():
            draw_digit(screen, cursor_x, y, int(char), scale)
            cursor_x += 8 * scale + scale
        else:
            cursor_x += 5 * scale  # Неизвестный символ - просто отступ


def draw_time(screen, x: int, y: int, hours: int, minutes: int, seconds: int, scale: int = 2):
    """
    Нарисовать время в формате HH:MM:SS

    Args:
        screen: Объект Screen
        x: X координата
        y: Y координата
        hours: Часы (0-23)
        minutes: Минуты (0-59)
        seconds: Секунды (0-59)
        scale: Масштаб
    """
    time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    draw_text_5x7(screen, x, y, time_str, scale)

