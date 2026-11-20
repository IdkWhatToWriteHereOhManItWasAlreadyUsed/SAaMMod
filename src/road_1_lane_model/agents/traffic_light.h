#pragma once

#include <memory>

#include "i_agent.h"
#include "i_run.h"

namespace resources { class road_segment; }

namespace agents
{
    enum class dispatch_mode
    {
        fixed,      // фиксированные t_green / t_red
        clearance,  // следующий зелёный только после полного освобождения участка
        adaptive    // зелёный по нагрузке + clearance вместо t_red
    };

    class traffic_light : public runner::i_agent,
                          public std::enable_shared_from_this<traffic_light>
    {
    public:
        traffic_light(resources::road_segment& road,
                      double_t t_green,
                      double_t t_red,
                      dispatch_mode mode = dispatch_mode::fixed);
        int id() const override;
        char phase() const;
        void switch_to(runner::i_run& run, char direction);
        void switch_to_none(runner::i_run& run);

        // Уведомление от машины: она покинула участок. Нужно для clearance.
        void on_car_exit(runner::i_run& run);

        // Уведомление о приходе машины: нужно для оценки интенсивности
        // прихода в adaptive-режиме.
        void on_car_arrival(char direction);

        // Новые длительности применяются к следующим фазам; текущая фаза
        // доигрывается с той длительностью, с которой была запущена.
        void set_t_green(double_t t_green);
        void set_t_red(double_t t_red);
    private:
        double_t green_duration(char direction, double_t now) const;
        double_t arrival_rate(int index, double_t now) const;
        void wake_up_queue(runner::i_run& run, char direction) const;

        resources::road_segment& road_;
        double_t t_green_;
        double_t t_red_;
        char phase_;
        dispatch_mode mode_;

        // Для adaptive (индексы: 0 = A, 1 = B):
        // когда направление последний раз теряло зелёный, сколько машин
        // пришло всего и какая очередь была в момент отключения зелёного.
        double_t green_off_time_[2] = {0.0, 0.0};
        double_t arrivals_[2] = {0.0, 0.0};
        double_t queue_at_green_off_[2] = {0.0, 0.0};

        // clearance: направление, которое ждёт освобождения участка
        char pending_direction_ = 'N';
        bool waiting_clearance_ = false;
    };
}