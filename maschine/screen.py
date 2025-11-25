#!/usr/bin/env python3
"""
Maschine Mikro MK3 Screen Control
==================================

Управление монохромным экраном контроллера.

Характеристики:
- Один экран 128 x 32 пикселя
- Монохромный (черно-белый)
- Битовая карта: 0 = пиксель включен, 1 = выключен
"""

from typing import Optional


# HID headers для передачи экрана
HEADER_HI = bytes([0xe0, 0x00, 0x00, 0x00, 0x00, 0x80, 0x00, 0x02, 0x00])
HEADER_LO = bytes([0xe0, 0x00, 0x00, 0x02, 0x00, 0x80, 0x00, 0x02, 0x00])

# Размеры экрана
SCREEN_WIDTH = 128
SCREEN_HEIGHT = 32  # Mikro MK3 has 128x32 screen, not 128x64!
SCREEN_BUFFER_SIZE = 512  # 128 * 32 / 8


class Screen:
    """Управление экраном контроллера"""

    def __init__(self):
        """Инициализация экрана"""
        # Buffer: 512 байт (128x32 bits)
        # 0xff = все пиксели выключены (инвертированная логика!)
        self.buffer = bytearray([0xff] * SCREEN_BUFFER_SIZE)

    def clear(self):
        """Очистить экран (все пиксели выключены)"""
        self.buffer = bytearray([0xff] * SCREEN_BUFFER_SIZE)

    def fill(self):
        """Заполнить экран (все пиксели включены)"""
        self.buffer = bytearray([0x00] * SCREEN_BUFFER_SIZE)

    def get_pixel(self, x: int, y: int) -> bool:
        """
        Получить состояние пикселя

        Args:
            x: Координата X (0-127)
            y: Координата Y (0-63)

        Returns:
            True если пиксель включен, False если выключен
        """
        if not (0 <= x < SCREEN_WIDTH and 0 <= y < SCREEN_HEIGHT):
            return False

        chunk = y // 8
        y_mod = y % 8
        idx = chunk * SCREEN_WIDTH + x

        # Инвертированная логика: 0 = включен
        return (self.buffer[idx] & (1 << y_mod)) == 0

    def set_pixel(self, x: int, y: int, on: bool = True):
        """
        Установить состояние пикселя

        Args:
            x: Координата X (0-127)
            y: Координата Y (0-31)
            on: True = включить, False = выключить
        """
        if not (0 <= x < SCREEN_WIDTH and 0 <= y < SCREEN_HEIGHT):
            return

        chunk = y // 8
        y_mod = y % 8
        idx = chunk * SCREEN_WIDTH + x
        mask = 1 << y_mod

        if on:
            # Включить пиксель (сбросить бит)
            self.buffer[idx] &= ~mask
        else:
            # Выключить пиксель (установить бит)
            self.buffer[idx] |= mask

    def draw_line(self, x0: int, y0: int, x1: int, y1: int, on: bool = True):
        """
        Нарисовать линию (алгоритм Брезенхема)

        Args:
            x0, y0: Начальная точка
            x1, y1: Конечная точка
            on: True = включить пиксели, False = выключить
        """
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy

        x, y = x0, y0

        while True:
            self.set_pixel(x, y, on)

            if x == x1 and y == y1:
                break

            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy

    def draw_rect(self, x: int, y: int, w: int, h: int, filled: bool = False, on: bool = True):
        """
        Нарисовать прямоугольник

        Args:
            x, y: Верхний левый угол
            w, h: Ширина и высота
            filled: True = заполненный, False = только контур
            on: True = включить пиксели, False = выключить
        """
        if filled:
            for i in range(h):
                for j in range(w):
                    self.set_pixel(x + j, y + i, on)
        else:
            # Верхняя и нижняя линии
            for j in range(w):
                self.set_pixel(x + j, y, on)
                self.set_pixel(x + j, y + h - 1, on)

            # Левая и правая линии
            for i in range(h):
                self.set_pixel(x, y + i, on)
                self.set_pixel(x + w - 1, y + i, on)

    def draw_circle(self, xc: int, yc: int, r: int, filled: bool = False, on: bool = True):
        """
        Нарисовать окружность (алгоритм средней точки)

        Args:
            xc, yc: Центр окружности
            r: Радиус
            filled: True = заполненный круг, False = только контур
            on: True = включить пиксели, False = выключить
        """
        x = 0
        y = r
        d = 1 - r

        def draw_points(px, py):
            if filled:
                # Заполненный круг - рисуем горизонтальные линии
                self.draw_line(xc - px, yc + py, xc + px, yc + py, on)
                self.draw_line(xc - px, yc - py, xc + px, yc - py, on)
                self.draw_line(xc - py, yc + px, xc + py, yc + px, on)
                self.draw_line(xc - py, yc - px, xc + py, yc - px, on)
            else:
                # Контур окружности - 8 точек симметрии
                self.set_pixel(xc + px, yc + py, on)
                self.set_pixel(xc - px, yc + py, on)
                self.set_pixel(xc + px, yc - py, on)
                self.set_pixel(xc - px, yc - py, on)
                self.set_pixel(xc + py, yc + px, on)
                self.set_pixel(xc - py, yc + px, on)
                self.set_pixel(xc + py, yc - px, on)
                self.set_pixel(xc - py, yc - px, on)

        while x <= y:
            draw_points(x, y)
            x += 1

            if d < 0:
                d += 2 * x + 1
            else:
                y -= 1
                d += 2 * (x - y) + 1

    def draw_text(self, x: int, y: int, text: str, font=None, on: bool = True):
        """
        Нарисовать текст (требует внешнего шрифта)

        Args:
            x, y: Начальная позиция
            text: Текст для отрисовки
            font: Словарь {char: bitmap} (опционально)
            on: True = включить пиксели, False = выключить
        """
        if font is None:
            # Используем встроенный простой шрифт для цифр
            from .screen_font import draw_digit

            cursor_x = x
            for char in text:
                if char.isdigit():
                    draw_digit(self, cursor_x, y, int(char))
                    cursor_x += 10  # Ширина цифры + отступ
                elif char == ' ':
                    cursor_x += 5
                else:
                    # Неизвестный символ - пропускаем
                    cursor_x += 5
        else:
            # Пользовательский шрифт
            cursor_x = x
            for char in text:
                if char in font:
                    bitmap = font[char]
                    for i, row in enumerate(bitmap):
                        for j, pixel in enumerate(row):
                            if pixel:
                                self.set_pixel(cursor_x + j, y + i, on)
                    cursor_x += len(bitmap[0]) + 1  # Ширина символа + отступ
                else:
                    cursor_x += 5  # Отступ для неизвестного символа

    def write(self, device) -> bool:
        """
        Отправить содержимое экрана на устройство

        Args:
            device: HID device object

        Returns:
            True если успешно, False если ошибка
        """
        try:
            # Отправляем верхнюю половину
            msg_hi = bytearray(HEADER_HI) + self.buffer[:256]
            device.write(msg_hi)

            # Отправляем нижнюю половину
            msg_lo = bytearray(HEADER_LO) + self.buffer[256:]
            device.write(msg_lo)

            return True
        except Exception as e:
            print(f"Error writing to screen: {e}")
            return False


def create_demo_pattern(screen: Screen):
    """Создать демонстрационный паттерн на экране"""
    screen.clear()

    # Рамка
    screen.draw_rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, filled=False, on=True)

    # Диагональные линии
    screen.draw_line(0, 0, SCREEN_WIDTH - 1, SCREEN_HEIGHT - 1, on=True)
    screen.draw_line(SCREEN_WIDTH - 1, 0, 0, SCREEN_HEIGHT - 1, on=True)

    # Центральная окружность
    screen.draw_circle(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, 12, filled=False, on=True)

    # Маленькие окружности в углах
    screen.draw_circle(8, 8, 6, filled=True, on=True)
    screen.draw_circle(SCREEN_WIDTH - 8, 8, 6, filled=True, on=True)
    screen.draw_circle(8, SCREEN_HEIGHT - 8, 6, filled=True, on=True)
    screen.draw_circle(SCREEN_WIDTH - 8, SCREEN_HEIGHT - 8, 6, filled=True, on=True)

