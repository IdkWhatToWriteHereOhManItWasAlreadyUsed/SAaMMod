#include "traffic_light.h"

#include <algorithm>

#include "logger.h"
#include "road_1_lane_model/resources/road_segment.h"
#include "road_1_lane_model/agents/car.h"

namespace agents
{
    namespace
    {
        // Границы адаптивного зелёного времени, сек.
        constexpr double_t ADAPTIVE_GREEN_MIN = 30.0;
        constexpr double_t ADAPTIVE_GREEN_MAX = 90.0;
        // Сколько секунд зелёного добавлять за каждую машину разницы очередей.
        constexpr double_t ADAPTIVE_GAIN = 1.0;
    }

    traffic_light::traffic_light(resources::road_segment& road,
                                 double_t t_green,
                                 double_t t_red,
                                 const dispatch_mode mode)
        : road_(road)
        , t_green_(t_green)
        , t_red_(t_red)
        , phase_('N')
        , mode_(mode)
    {
    }

    int traffic_light::id() const { return 0; }

    char traffic_light::phase() const { return phase_; }

    void traffic_light::set_t_green(const double_t t_green) { t_green_ = t_green; }
    void traffic_light::set_t_red(const double_t t_red) { t_red_ = t_red; }

    double_t traffic_light::green_duration(const char direction) const
    {
        if (mode_ != dispatch_mode::adaptive)
        {
            return t_green_;
        }

        // Адаптация: базовое время корректируется на разницу очередей.
        // Демпфирование (gain = 1 с на машину) не даёт одной очереди
        // забрать почти всё зелёное время при случайных колебаниях.
        const double_t qa = static_cast<double_t>(road_.queue_size('A'));
        const double_t qb = static_cast<double_t>(road_.queue_size('B'));
        const double_t own = (direction == 'A') ? qa : qb;
        const double_t other = (direction == 'A') ? qb : qa;
        const double_t diff = own - other;

        // Мёртвая зона: при близких очередях не дёргаем зелёный зря.
        if (std::abs(diff) < 2.0)
        {
            return t_green_;
        }

        return std::clamp(t_green_ + ADAPTIVE_GAIN * diff,
                          ADAPTIVE_GREEN_MIN,
                          ADAPTIVE_GREEN_MAX);
    }

    void traffic_light::switch_to(runner::i_run& run, const char direction)
    {
        auto self = shared_from_this();
        run.move_active_event
        (
            green_duration(direction),
            [self](runner::i_run& r) { self->switch_to_none(r); }
        );

        const char previous = phase_;
        phase_ = direction;
        wake_up_queue(run, direction);

        logging::logger::instance().write_light(run.model_time(), previous, phase_);
    }

    void traffic_light::switch_to_none(runner::i_run& run)
    {
        const char previous = phase_;
        phase_ = 'N';

        const char next = (previous == 'A') ? 'B' : 'A';

        logging::logger::instance().write_light(run.model_time(), previous, phase_);

        if (mode_ == dispatch_mode::clearance)
        {
            pending_direction_ = next;

            if (road_.empty())
            {
                // Участок уже свободен — ждать нечего.
                waiting_clearance_ = false;
                auto self = shared_from_this();
                run.move_active_event
                (
                    0.0,
                    [self, next](runner::i_run& r) { self->switch_to(r, next); }
                );
            }
            else
            {
                // Ждём on_car_exit() от последней машины на участке.
                waiting_clearance_ = true;
                run.delete_active_event();
            }
            return;
        }

        auto self = shared_from_this();
        run.move_active_event
        (
            t_red_,
            [self, next](runner::i_run& r) { self->switch_to(r, next); }
        );
    }

    void traffic_light::on_car_exit(runner::i_run& run)
    {
        if (mode_ != dispatch_mode::clearance || !waiting_clearance_)
        {
            return;
        }
        if (!road_.empty())
        {
            return;
        }

        waiting_clearance_ = false;
        const char next = pending_direction_;
        pending_direction_ = 'N';

        auto self = shared_from_this();
        run.new_event
        (
            self,
            [self, next](runner::i_run& r) { self->switch_to(r, next); },
            run.model_time()
        );
    }

    void traffic_light::wake_up_queue(runner::i_run& run, char direction) const
    {
        if (!road_.is_free())
        {
            return;
        }
        if (road_.queue_empty(direction))
        {
            return;
        }

        auto car = road_.pop(direction);
        if (!car)
        {
            return;
        }

        run.new_event
        (
            car,
            [car](runner::i_run& r) { car->start_driving(r); },
            run.model_time()
        );
    }
}
