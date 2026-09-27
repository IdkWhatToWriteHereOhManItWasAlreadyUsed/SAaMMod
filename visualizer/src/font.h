#pragma once

#include <string>

struct SDL_Renderer;

namespace font
{
    struct color
    {
        unsigned char r = 235;
        unsigned char g = 235;
        unsigned char b = 235;
    };

    // Инициализация SDL_ttf и загрузка шрифта. Берёт первый существующий файл
    // из списка, чтобы не зависеть от одного конкретного дистрибутива.
    // Бросает std::runtime_error, если не нашлось ни одного шрифта.
    void init();
    void shutdown();

    bool ready();

    // Кегль в пикселях
    void set_size(float size);
    float size();

    // Ширина строки при текущем кегле
    int text_width(const std::string& text);

    // Высота строки при текущем кегле
    int text_height(const std::string& text);

    // Текст левым верхним углом в точке (x, y)
    void draw_text(SDL_Renderer* renderer,
                   float x,
                   float y,
                   const std::string& text,
                   const color& text_color = color{},
                   float size = 0);

    // Текст по центру прямоугольника (x, y, w, h) — ширина прямоугольника
    // от длины подписи не зависит
    void draw_text_centered(SDL_Renderer* renderer,
                            float x,
                            float y,
                            float w,
                            float h,
                            const std::string& text,
                            const color& text_color = color{},
                            float size = 0);
}
