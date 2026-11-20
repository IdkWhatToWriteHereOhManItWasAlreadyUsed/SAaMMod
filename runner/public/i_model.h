#pragma once
#include <cmath>
#include <string>
#include <string_view>

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

        // Изменение параметра модели во время прогона. Имя параметра задаётся
        // строкой, значение — числом. Модель сама решает, какие имена она
        // поддерживает; по умолчанию не поддерживается ни один.
        virtual bool set_parameter(std::string_view /*name*/, double_t /*value*/)
        {
            return false;
        }

        virtual ~i_model() = default;
    };
}
