#pragma once

#include <cstddef>
#include <vector>

#include "trace.h"

namespace scene
{
    struct waiting_car
    {
        int id = 0;
        char direction = 'A';
    };

    struct moving_car
    {
        int id = 0;
        char direction = 'A';
        double enter_time = 0;
        double leave_time = 0;
    };

    // Состояние процесса на заданный момент модельного времени.
    // События применяются строго по порядку, поэтому картинка зависит только
    // от времени, а не от того, как быстро мы его перематывали.
    class scene
    {
    public:
        explicit scene(const trace::data& data);

        // Вернуться к началу прогона
        void reset();

        // Применить все события, попавшие в model_time. При перемотке назад
        // состояние пересобирается с нуля.
        void advance_to(double model_time);

        double begin_time() const;
        double end_time() const;
        double time() const;
        char light_phase() const;

        // Все ожидающие машины в порядке прибытия, вперемешку по направлениям
        const std::vector<waiting_car>& waiting() const;
        const std::vector<moving_car>& moving() const;

    private:
        const trace::car_event* next_car() const;
        const trace::light_event* next_light() const;

        void apply(const trace::car_event& event);
        void apply(const trace::light_event& event);
        void drop_from_queue(char direction);
        void drop_from_road(int id);

        const trace::data& data_;
        std::size_t car_cursor_ = 0;
        std::size_t light_cursor_ = 0;
        double time_ = 0;
        char phase_ = 'N';
        std::vector<waiting_car> waiting_;
        std::vector<moving_car> moving_;
    };
}
