#include <algorithm>
#include <cstdlib>
#include <exception>
#include <iostream>
#include <string>

#include <SDL3/SDL.h>

#include "render.h"
#include "scene.h"
#include "trace.h"

namespace
{
    constexpr double default_speed = 4.0;
    constexpr double max_scroll = 500.0;

    bool is_number_key(const SDL_Keycode key, int& digit)
    {
        if (key < SDLK_0 || key > SDLK_9)
        {
            return false;
        }

        digit = key - SDLK_0;
        return true;
    }
}

int main(int argc, char** argv)
{
   // if (argc < 2)
    {
        std::cerr << "usage: " << argv[0] << " <trace.jsonl> [speed]\n"
                  << "  speed — во сколько раз быстрее модельного времени, по умолчанию "
                  << default_speed << "\n";
      //  return EXIT_FAILURE;
    }

    const std::string path = "/home/dmitry/CLionProjects/SAiMMOD_Lab2/lab2/Lab2_Code/logs/road_1_lane.jsonl";//argv[1];

    double speed = default_speed;
    if (argc >= 3)
    {
        speed = std::atof(argv[2]);
        if (!(speed > 0))
        {
            speed = default_speed;
        }
    }

    trace::data data;
    try
    {
        data = trace::load(path);
    }
    catch (const std::exception& error)
    {
        std::cerr << "не удалось прочитать лог: " << error.what() << "\n";
        return EXIT_FAILURE;
    }

    if (!SDL_Init(SDL_INIT_VIDEO))
    {
        std::cerr << "SDL_Init: " << SDL_GetError() << "\n";
        return EXIT_FAILURE;
    }

    SDL_Window* window = SDL_CreateWindow("Road trace",
                                          render::layout::window_width,
                                          render::layout::window_height,
                                          0);
    if (window == nullptr)
    {
        std::cerr << "SDL_CreateWindow: " << SDL_GetError() << "\n";
        SDL_Quit();
        return EXIT_FAILURE;
    }

    SDL_Renderer* renderer = SDL_CreateRenderer(window, nullptr);
    if (renderer == nullptr)
    {
        std::cerr << "SDL_CreateRenderer: " << SDL_GetError() << "\n";
        SDL_DestroyWindow(window);
        SDL_Quit();
        return EXIT_FAILURE;
    }

    scene::scene state(data);
    state.advance_to(data.begin_time);

    bool running = true;
    bool paused = false;
    bool restart = false;
    bool jump_to_end = false;
    double model_time = data.begin_time;
    double scroll = 0;

    Uint64 previous = SDL_GetPerformanceCounter();
    const auto frequency = static_cast<double>(SDL_GetPerformanceFrequency());

    while (running)
    {
        SDL_Event event;
        while (SDL_PollEvent(&event) != false)
        {
            if (event.type == SDL_EVENT_QUIT)
            {
                running = false;
            }
            else if (event.type == SDL_EVENT_MOUSE_WHEEL)
            {
                scroll = std::clamp(scroll - static_cast<double>(event.wheel.y) * render::layout::queue_step,
                                    -max_scroll,
                                    max_scroll);
            }
            else if (event.type == SDL_EVENT_KEY_DOWN && event.key.repeat == false)
            {
                int digit = 0;
                if (is_number_key(event.key.key, digit))
                {
                    // цифры вводит множитель скорости: пробел сбрасывает на 4
                    speed = static_cast<double>(digit == 0 ? 10 : digit);
                }
                else
                {
                    switch (event.key.key)
                    {
                        case SDLK_ESCAPE:
                        case SDLK_Q:
                            running = false;
                            break;

                        case SDLK_SPACE:
                            restart = false;
                            jump_to_end = false;
                            paused = !paused;
                            break;

                        case SDLK_R:
                            restart = true;
                            jump_to_end = false;
                            paused = true;
                            break;

                        case SDLK_E:
                            jump_to_end = true;
                            restart = false;
                            paused = true;
                            break;

                        case SDLK_EQUALS:
                        case SDLK_PLUS:
                            speed *= 1.25;
                            break;

                        case SDLK_MINUS:
                            speed /= 1.25;
                            break;

                        default:
                            break;
                    }
                }
            }
        }

        if (restart)
        {
            model_time = data.begin_time;
            scroll = 0;
            state.reset();
            restart = false;
        }

        if (jump_to_end)
        {
            model_time = data.end_time;
            jump_to_end = false;
        }

        const Uint64 now = SDL_GetPerformanceCounter();
        const double frame = static_cast<double>(now - previous) / frequency;
        previous = now;

        if (!paused)
        {
            model_time += frame * speed;
            if (model_time >= data.end_time)
            {
                model_time = data.end_time;
                paused = true;
            }
        }

        state.advance_to(model_time);
        render::draw(renderer, state, speed, paused, scroll);

        SDL_RenderPresent(renderer);
    }

    SDL_DestroyRenderer(renderer);
    SDL_DestroyWindow(window);
    SDL_Quit();
    return EXIT_SUCCESS;
}
