#include "font.h"

#include <array>
#include <stdexcept>

#include <SDL3/SDL.h>
#include <SDL3_ttf/SDL_ttf.h>

namespace font
{
    namespace
    {
        // Узкий шрифт: id из четырёх цифр должен помещаться в прямоугольник
        // машины шириной 34 пикселя
        const std::array<const char*, 6> font_candidates = {
            "/usr/share/fonts/TTF/DejaVuSansCondensed-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf",
            "/usr/share/fonts/TTF/FiraSansCondensed-Bold.ttf",
            "/usr/share/fonts/TTF/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        };

        TTF_Font* handle = nullptr;
        float current_size = 12.0f;

        TTF_Font* load_font(const float size)
        {
            for (const char* path : font_candidates)
            {
                SDL_PathInfo info;
                if (!SDL_GetPathInfo(path, &info))
                {
                    continue;
                }

                TTF_Font* font = TTF_OpenFont(path, size);
                if (font != nullptr)
                {
                    TTF_SetFontDirection(font, TTF_DIRECTION_LTR);
                    return font;
                }
            }

            throw std::runtime_error("не найден ни один ttf-шрифт из списка font_candidates");
        }
    }

    void init()
    {
        if (handle != nullptr)
        {
            return;
        }

        if (!TTF_Init())
        {
            throw std::runtime_error(std::string("TTF_Init: ") + SDL_GetError());
        }

        try
        {
            handle = load_font(current_size);
        }
        catch (...)
        {
            TTF_Quit();
            throw;
        }
    }

    void shutdown()
    {
        if (handle != nullptr)
        {
            TTF_CloseFont(handle);
            handle = nullptr;
        }

        TTF_Quit();
    }

    bool ready()
    {
        return handle != nullptr;
    }

    void set_size(const float size)
    {
        if (handle == nullptr || size <= 0)
        {
            return;
        }

        if (TTF_SetFontSize(handle, size))
        {
            current_size = size;
        }
    }

    float size()
    {
        return current_size;
    }

    int text_width(const std::string& text)
    {
        if (handle == nullptr || text.empty())
        {
            return 0;
        }

        int width = 0;
        int height = 0;
        if (!TTF_GetStringSize(handle, text.c_str(), text.size(), &width, &height))
        {
            return 0;
        }

        return width;
    }

    int text_height(const std::string& text)
    {
        if (handle == nullptr || text.empty())
        {
            return 0;
        }

        int width = 0;
        int height = 0;
        if (!TTF_GetStringSize(handle, text.c_str(), text.size(), &width, &height))
        {
            return 0;
        }

        return height;
    }

    void draw_text(SDL_Renderer* renderer,
                   const float x,
                   const float y,
                   const std::string& text,
                   const color& text_color,
                   const float text_size)
    {
        if (handle == nullptr || text.empty())
        {
            return;
        }

        if (text_size > 0 && text_size != current_size)
        {
            set_size(text_size);
        }

        const SDL_Color sdl_color{text_color.r, text_color.g, text_color.b, 255};

        // Готовим один surface, а не текстуру: текст на кадре один и тот же
        // десятки раз, кэшировать текстуры ради этого дороже, чем пересоздать
        SDL_Surface* surface = TTF_RenderText_Blended(handle, text.c_str(), text.size(), sdl_color);
        if (surface == nullptr)
        {
            return;
        }

        if (SDL_Texture* texture = SDL_CreateTextureFromSurface(renderer, surface))
        {
            const SDL_FRect target{x, y, static_cast<float>(surface->w), static_cast<float>(surface->h)};
            SDL_RenderTexture(renderer, texture, nullptr, &target);
            SDL_DestroyTexture(texture);
        }

        SDL_DestroySurface(surface);
    }

    void draw_text_centered(SDL_Renderer* renderer,
                            const float x,
                            const float y,
                            const float w,
                            const float h,
                            const std::string& text,
                            const color& text_color,
                            const float text_size)
    {
        if (handle == nullptr || text.empty())
        {
            return;
        }

        if (text_size > 0 && text_size != current_size)
        {
            set_size(text_size);
        }

        const int width = text_width(text);
        int height = 0;
        TTF_GetStringSize(handle, text.c_str(), text.size(), nullptr, &height);

        draw_text(renderer,
                  x + (w - static_cast<float>(width)) / 2.0f,
                  y + (h - static_cast<float>(height)) / 2.0f,
                  text,
                  text_color);
    }
}
