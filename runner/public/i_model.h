#pragma once
#include <cmath>
#include <string>

namespace runner
{
    class i_run;

    class i_model
    {
    public:
        virtual void reset(i_run& run) = 0;
        virtual void stop(i_run& run) = 0;

        // Точка сбора статистики: раннер вызывает её в начале прогона и после
        // каждого события, когда состояние модели уже актуально для model_time().
        // По умолчанию ничего не делает.
        virtual void sample(i_run& run) { (void) run; }

        virtual ~i_model() = default;
    };
}
