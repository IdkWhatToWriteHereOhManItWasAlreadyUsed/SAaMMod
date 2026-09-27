#include "font.h"

#include <vector>

#include <SDL3/SDL.h>

namespace font
{
    namespace
    {
        constexpr int glyph_width = 5;
        constexpr int glyph_height = 7;
        constexpr int glyph_spacing = 1;

        // Глиф — это 5 столбцов, в каждом байте бит i отвечает за строку i
        const unsigned char glyph_digits[10][5] = {
            {0x3E, 0x51, 0x49, 0x45, 0x3E},
            {0x00, 0x42, 0x7F, 0x40, 0x00},
            {0x42, 0x61, 0x51, 0x49, 0x46},
            {0x21, 0x41, 0x45, 0x4B, 0x31},
            {0x18, 0x14, 0x12, 0x7F, 0x10},
            {0x27, 0x45, 0x45, 0x45, 0x39},
            {0x3C, 0x4A, 0x49, 0x49, 0x30},
            {0x01, 0x71, 0x09, 0x05, 0x03},
            {0x36, 0x49, 0x49, 0x49, 0x36},
            {0x06, 0x49, 0x49, 0x29, 0x1E},
        };

        const unsigned char glyph_upper[26][5] = {
            {0x7E, 0x11, 0x11, 0x11, 0x7E},
            {0x7F, 0x49, 0x49, 0x49, 0x36},
            {0x3E, 0x41, 0x41, 0x41, 0x22},
            {0x7F, 0x41, 0x41, 0x22, 0x1C},
            {0x7F, 0x49, 0x49, 0x49, 0x41},
            {0x7F, 0x09, 0x09, 0x01, 0x01},
            {0x3E, 0x41, 0x49, 0x49, 0x7A},
            {0x7F, 0x08, 0x08, 0x08, 0x7F},
            {0x00, 0x41, 0x7F, 0x41, 0x00},
            {0x20, 0x40, 0x41, 0x3F, 0x01},
            {0x7F, 0x08, 0x14, 0x22, 0x41},
            {0x7F, 0x40, 0x40, 0x40, 0x40},
            {0x7F, 0x02, 0x0C, 0x02, 0x7F},
            {0x7F, 0x04, 0x08, 0x10, 0x7F},
            {0x3E, 0x41, 0x41, 0x41, 0x3E},
            {0x7F, 0x09, 0x09, 0x09, 0x06},
            {0x3E, 0x41, 0x51, 0x21, 0x5E},
            {0x7F, 0x09, 0x19, 0x29, 0x46},
            {0x46, 0x49, 0x49, 0x49, 0x31},
            {0x01, 0x01, 0x7F, 0x01, 0x01},
            {0x3F, 0x40, 0x40, 0x40, 0x3F},
            {0x1F, 0x20, 0x40, 0x20, 0x1F},
            {0x7F, 0x20, 0x18, 0x20, 0x7F},
            {0x63, 0x14, 0x08, 0x14, 0x63},
            {0x03, 0x04, 0x78, 0x04, 0x03},
            {0x61, 0x51, 0x49, 0x45, 0x43},
        };

        const unsigned char glyph_space[5] = {0x00, 0x00, 0x00, 0x00, 0x00};
        const unsigned char glyph_dot[5] = {0x00, 0x60, 0x60, 0x00, 0x00};
        const unsigned char glyph_colon[5] = {0x00, 0x36, 0x36, 0x00, 0x00};
        const unsigned char glyph_dash[5] = {0x08, 0x08, 0x08, 0x08, 0x08};
        const unsigned char glyph_slash[5] = {0x20, 0x10, 0x08, 0x04, 0x02};
        const unsigned char glyph_lower_x[5] = {0x00, 0x11, 0x0E, 0x11, 0x00};

        const unsigned char* glyph_of(const char c)
        {
            if (c >= '0' && c <= '9') return glyph_digits[c - '0'];
            if (c >= 'A' && c <= 'Z') return glyph_upper[c - 'A'];

            switch (c)
            {
                case '.': return glyph_dot;
                case ':': return glyph_colon;
                case '-': return glyph_dash;
                case '/': return glyph_slash;
                case 'x': return glyph_lower_x;
                default: return glyph_space;
            }
        }
    }

    int text_width(const std::string& text, const int scale)
    {
        if (text.empty())
        {
            return 0;
        }

        const int advance = (glyph_width + glyph_spacing) * scale;
        return static_cast<int>(text.size()) * advance - glyph_spacing * scale;
    }

    void draw_text(SDL_Renderer* renderer,
                   const float x,
                   const float y,
                   const std::string& text,
                   const color& text_color,
                   const int scale)
    {
        if (text.empty())
        {
            return;
        }

        // Собираем все пиксели текста в один массив и рисуем одним вызовом:
        // на кадре подписей сотни, и по одному SDL_RenderFillRect на пиксель
        // Renderer дёргать слишком дорого
        std::vector<SDL_FRect> pixels;
        pixels.reserve(text.size() * 12);

        const auto step = static_cast<float>(scale);
        float pen = x;

        for (const char c : text)
        {
            const unsigned char* columns = glyph_of(c);

            for (int column = 0; column < glyph_width; ++column)
            {
                for (int row = 0; row < glyph_height; ++row)
                {
                    if (((columns[column] >> row) & 1) == 0)
                    {
                        continue;
                    }

                    pixels.push_back({pen + static_cast<float>(column) * step,
                                      y + static_cast<float>(row) * step,
                                      step,
                                      step});
                }
            }

            pen += static_cast<float>((glyph_width + glyph_spacing) * scale);
        }

        SDL_SetRenderDrawColor(renderer, text_color.r, text_color.g, text_color.b, 255);
        SDL_RenderFillRects(renderer, pixels.data(), static_cast<int>(pixels.size()));
    }
}
