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
        // Сколько секунд зелёного добавлять за каждую машину разницы
        // накопленной нагрузки и мёртвая зона этой разницы.
        constexpr double_t ADAPTIVE_GAIN = 1.0;
        constexpr double_t ADAPTIVE_DEADBAND = 5.0;

        int index_of(const char direction)
        {
            return direction == 'A' ? 0 : 1;
        }
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

    double_t traffic_light::arrival_rate(const int index,
                                         const double_t now) const
    {
        return (now > 0.0) ? arrivals_[index] / now : 0.0;
    }

    double_t traffic_light::green_duration(const char direction,
                                           const double_t now) const
    {
        if (mode_ != dispatch_mode::adaptive)
        {
            return t_green_;
        }

        // Нагрузка направления = текущая очередь плюс прогноз прихода
        // на ближайшее время. Темп прихода оценивается как среднее между
        // средней интенсивностью по прогону и фактическим приростом
        // очереди за последний красный (q_on - q_off) / red.
        const int own_index = index_of(direction);
        const int other_index = 1 - own_index;
        const char other_direction = (direction == 'A') ? 'B' : 'A';

        const auto own_queue =
            static_cast<double_t>(road_.queue_size(direction));
        const auto other_queue =
            static_cast<double_t>(road_.queue_size(other_direction));

        const auto own_red =
            std::max(0.0, now - green_off_time_[own_index]);
        const auto other_red =
            std::max(0.0, now - green_off_time_[other_index]);

        const auto own_growth =
            std::max(0.0, own_queue - queue_at_green_off_[own_index]);
        const auto other_growth =
            std::max(0.0, other_queue - queue_at_green_off_[other_index]);

        const auto own_avg_rate = arrival_rate(own_index, now);
        const auto other_avg_rate = arrival_rate(other_index, now);
        const auto own_red_rate =
            (own_red > 1e-9) ? own_growth / own_red : own_avg_rate;
        const auto other_red_rate =
            (other_red > 1e-9) ? other_growth / other_red : other_avg_rate;

        const auto own_rate = 0.5 * (own_avg_rate + own_red_rate);
        const auto other_rate = 0.5 * (other_avg_rate + other_red_rate);

        // Горизонт прогноза — базовое зелёное время.
        const auto own_load = own_queue + own_rate * t_green_;
        const auto other_load = other_queue + other_rate * t_green_;

        const auto diff = own_load - other_load;

        // Мёртвая зона: при близких нагрузках не дёргаем зелёный зря.
        if (std::abs(diff) < ADAPTIVE_DEADBAND)
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
            green_duration(direction, run.model_time()),
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

        const int previous_index = index_of(previous);
        green_off_time_[previous_index] = run.model_time();
        queue_at_green_off_[previous_index] =
            static_cast<double_t>(road_.queue_size(previous));

        const char next = (previous == 'A') ? 'B' : 'A';

        logging::logger::instance().write_light(run.model_time(), previous, phase_);

        if (mode_ == dispatch_mode::clearance ||
            mode_ == dispatch_mode::adaptive)
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
        if ((mode_ != dispatch_mode::clearance &&
             mode_ != dispatch_mode::adaptive) ||
            !waiting_clearance_)
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

    void traffic_light::on_car_arrival(const char direction)
    {
        arrivals_[index_of(direction)] += 1.0;
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
