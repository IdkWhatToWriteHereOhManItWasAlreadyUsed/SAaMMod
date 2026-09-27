#include "render.h"

#include <algorithm>
#include <cmath>
#include <string>

#include <SDL3/SDL.h>

#include "font.h"

namespace render
{
    namespace
    {
        struct rgb
        {
            unsigned char r;
            unsigned char g;
            unsigned char b;
        };

        constexpr rgb background{26, 30, 36};
        constexpr rgb road_color{116, 116, 122};
        constexpr rgb marking{232, 232, 232};
        constexpr rgb car_a{204, 62, 62};
        constexpr rgb car_b{62, 96, 214};
        constexpr rgb lamp_box{58, 62, 70};
        constexpr rgb lamp_green{64, 208, 96};
        constexpr rgb lamp_red{226, 64, 64};

        const font::color text_color{235, 235, 235};

        void fill(SDL_Renderer* renderer, const rect& r, const rgb& c)
        {
            SDL_SetRenderDrawColor(renderer, c.r, c.g, c.b, 255);
            const SDL_FRect target{r.x, r.y, r.w, r.h};
            SDL_RenderFillRect(renderer, &target);
        }

        std::string to_text(const double value, const int decimals)
        {
            char buffer[64];
            SDL_snprintf(buffer, sizeof(buffer), "%.*f", decimals, value);
            return buffer;
        }

        void fill_circle(SDL_Renderer* renderer, const float cx, const float cy, const float radius,
                         const rgb& c)
        {
            // Круг собираем из горизонтальных отрезков: так дешевле, чем считать
            // геометрию многоугольника, а выглядит ровно так же
            for (int dy = -static_cast<int>(radius); dy <= static_cast<int>(radius); ++dy)
            {
                const float d = static_cast<float>(dy);
                const float half = std::sqrt(radius * radius - d * d);
                fill(renderer, {cx - half, cy + d, half * 2.0f, 1.0f}, c);
            }
        }

        void draw_car(SDL_Renderer* renderer, const rect& slot, const char direction, const int id)
        {
            // Прямоугольник всегда одинаковой ширины: длина подписи на него не
            // влияет, id просто центрируется внутри
            fill(renderer, slot, direction == 'A' ? car_a : car_b);

            font::draw_text_centered(renderer,
                                     slot.x,
                                     slot.y,
                                     slot.w,
                                     slot.h,
                                     std::to_string(id),
                                     text_color,
                                     layout::car_font_size);
        }

        void draw_traffic_light(SDL_Renderer* renderer, const float x, const bool green)
        {
            const float y = static_cast<float>(layout::road_center_y - layout::road_height / 2
                                               - layout::light_size - 8);
            const auto size = static_cast<float>(layout::light_size);

            fill(renderer, {x, y, size, size}, lamp_box);

            const float radius = size / 2.0f - 6.0f;
            fill_circle(renderer, x + size / 2.0f, y + size / 2.0f, radius, green ? lamp_green : lamp_red);
        }

        bool offscreen(const rect& r)
        {
            return r.y + r.h < 0 || r.y > static_cast<float>(layout::window_height);
        }
    }

    rect waiting_slot(const char direction, const std::size_t position, const double scroll)
    {
        // Нулевая машина стоит ровно на линии дороги, каждая следующая отступает
        // на шаг по очереди: вверх, вниз, снова вверх и так далее
        double offset = 0;
        if (position > 0)
        {
            const auto steps = static_cast<double>((position + 1) / 2);
            offset = (position % 2 == 1) ? -steps * layout::queue_step
                                         : steps * layout::queue_step;
        }

        const float x = direction == 'A'
            ? static_cast<float>(layout::road_left - layout::queue_gap - layout::car_width)
            : static_cast<float>(layout::road_right + layout::queue_gap);

        return {x,
                static_cast<float>(layout::road_center_y + offset - scroll)
                    - static_cast<float>(layout::car_height) / 2.0f,
                static_cast<float>(layout::car_width),
                static_cast<float>(layout::car_height)};
    }

    rect moving_slot(const char direction, const double elapsed, const double speed)
    {
        // К x прибавляется расстояние, пройденное с момента въезда: машина
        // появляется в стартовой точке своей стороны ровно в момент enter
        const auto travelled = static_cast<float>(std::max(elapsed, 0.0) * speed);

        const float start = direction == 'A'
            ? static_cast<float>(layout::road_left + layout::car_width / 2.0)
            : static_cast<float>(layout::road_right - layout::car_width / 2.0);

        const float x = direction == 'A' ? start + travelled : start - travelled;

        return {x - static_cast<float>(layout::car_width) / 2.0f,
                static_cast<float>(layout::road_center_y)
                    - static_cast<float>(layout::car_height) / 2.0f,
                static_cast<float>(layout::car_width),
                static_cast<float>(layout::car_height)};
    }

    void draw(SDL_Renderer* renderer,
              const scene::scene& state,
              const double speed,
              const bool paused,
              const double scroll)
    {
        SDL_SetRenderDrawColor(renderer, background.r, background.g, background.b, 255);
        SDL_RenderClear(renderer);

        fill(renderer, {static_cast<float>(layout::road_left),
                        static_cast<float>(layout::road_center_y - layout::road_height / 2.0),
                        static_cast<float>(layout::road_right - layout::road_left),
                        static_cast<float>(layout::road_height)},
             road_color);

        for (int x = layout::road_left + 20; x < layout::road_right - 20; x += 40)
        {
            fill(renderer, {static_cast<float>(x),
                            static_cast<float>(layout::road_center_y) - 1.0f,
                            20.0f,
                            2.0f},
                 marking);
        }

        // Подписи направлений под дорогой, чтобы их не закрывали машины
        font::draw_text(renderer,
                        static_cast<float>(layout::road_left),
                        static_cast<float>(layout::road_center_y + layout::road_height / 2) + 8.0f,
                        "A",
                        text_color,
                        layout::label_font_size);
        font::draw_text(renderer,
                        static_cast<float>(layout::road_right) - 20.0f,
                        static_cast<float>(layout::road_center_y + layout::road_height / 2) + 8.0f,
                        "B",
                        text_color,
                        layout::label_font_size);

        const char phase = state.light_phase();
        draw_traffic_light(renderer, static_cast<float>(layout::road_left - layout::light_size), phase == 'A');
        draw_traffic_light(renderer, static_cast<float>(layout::road_right), phase == 'B');

        // Номер в очереди считаем отдельно для каждого направления, иначе
        // машины чередовались бы между A и B, а не внутри своей очереди
        std::size_t position_a = 0;
        std::size_t position_b = 0;

        for (const scene::waiting_car& car : state.waiting())
        {
            const std::size_t position = car.direction == 'A' ? position_a++ : position_b++;

            const rect slot = waiting_slot(car.direction, position, scroll);
            if (offscreen(slot))
            {
                // очередь бывает на 1800 машин, за окном рисовать незачем
                continue;
            }

            draw_car(renderer, slot, car.direction, car.id);
        }

        // Все машины едут с одной скоростью: длина дороги делённая на время
        // проезда. Скорость считается один раз на кадр, а позиция каждой
        // машины получается прибавлением к её x расстояния, пройденного с
        // момента въезда. Никакого выталкивания соседей: уехавшая первая
        // машина не должна сдвигать остальных.
        const double passage = state.passage_time();
        const double road_speed = passage > 0
            ? static_cast<double>(layout::road_right - layout::road_left) / passage
            : 0.0;

        for (const scene::moving_car& car : state.moving())
        {
            const rect slot = moving_slot(car.direction, state.time() - car.enter_time, road_speed);
            if (offscreen(slot) || slot.x + slot.w < layout::road_left || slot.x > layout::road_right)
            {
                continue;
            }

            draw_car(renderer, slot, car.direction, car.id);
        }

        const std::string info = "T=" + to_text(state.time(), 1) + " / "
                                 + to_text(state.end_time(), 1) + "  X" + to_text(speed, 2)
                                 + (paused ? "  PAUSED" : "") + "  QUEUE="
                                 + std::to_string(state.waiting().size()) + "  ROAD="
                                 + std::to_string(state.moving().size());

        font::draw_text(renderer, 12.0f, 10.0f, info, text_color, layout::hud_font_size);
        font::draw_text(renderer,
                        12.0f,
                        34.0f,
                        "SPACE PAUSE   R RESTART   E END   +/- SPEED   1-9 SPEED   WHEEL SCROLL   ESC QUIT",
                        text_color,
                        layout::help_font_size);
    }
}
