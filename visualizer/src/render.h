#pragma once

#include <cstddef>

struct SDL_Renderer;

#include "scene.h"

namespace render
{
    // Геометрия сцены в пикселях окна
    struct layout
    {
        static constexpr int window_width = 1280;
        static constexpr int window_height = 720;

        static constexpr int road_left = 300;
        static constexpr int road_right = 980;
        static constexpr int road_center_y = 360;
        static constexpr int road_height = 110;

        static constexpr int car_width = 34;
        static constexpr int car_height = 20;

        // Шаг «выше/ниже» для машин в очереди и отступ очереди от края дороги
        static constexpr int queue_step = 26;
        static constexpr int queue_gap = 60;

        static constexpr int light_size = 30;
    };

    struct rect
    {
        float x = 0;
        float y = 0;
        float w = 0;
        float h = 0;
    };

    // Положение ожидающей машины по её номеру в очереди своего направления:
    // 0 — ровно на уровне дороги, 1 — выше, 2 — ниже, 3 — выше, 4 — ниже, ...
    // Машины стоят у края дороги со своей стороны (A слева, B справа).
    rect waiting_slot(char direction, std::size_t position, double scroll);

    // Машина на дороге: progress от 0 (въезд) до 1 (отъезд)
    rect moving_slot(char direction, double progress);

    void draw(SDL_Renderer* renderer,
              const scene::scene& state,
              double speed,
              bool paused,
              double scroll);
}
