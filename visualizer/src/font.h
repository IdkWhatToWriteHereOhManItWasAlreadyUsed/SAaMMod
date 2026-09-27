#pragma once

#include <string>

struct SDL_Renderer;

namespace font
{
    // Встроенный шрифт 5x7: не тянем ttf-файл и зависимость от SDL_ttf,
    // а цифры и латиницы для подписей автомобилей хватает с запасом
    struct color
    {
        unsigned char r = 235;
        unsigned char g = 235;
        unsigned char b = 235;
    };

    int text_width(const std::string& text, int scale = 1);

    void draw_text(SDL_Renderer* renderer,
                   float x,
                   float y,
                   const std::string& text,
                   const color& text_color = color{},
                   int scale = 1);
}
