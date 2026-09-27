#include "car.h"

#include <iostream>
#include "road_1_lane_model/resources/road_segment.h"
#include "road_1_lane_model/agents/traffic_light.h"

namespace agents
{
    car::car(int id,
             char direction,
             resources::road_segment& road,
             agents::traffic_light& light)
        : id_(id)
        , direction_(direction)
        , road_(road)
        , light_(light)
    {
    }

    int car::id() const { return id_; }

    char car::direction() const { return direction_; }
    double_t car::arrival_time() const { return arrival_time_; }
    double_t car::drive_start_time() const { return drive_start_time_; }
    double_t car::departure_time() const { return departure_time_; }

    void car::arrive(runner::i_run& run)
    {
        arrival_time_ = run.model_time();
        std::cout << arrival_time_ << ": car " << id_ << " arrived to " << direction_ << std::endl;

        auto self = shared_from_this();

        if (light_.phase() == direction_) // зелёный в нужном направлении — заезжаем
        {
            run.next_active_event
            (
                [self](runner::i_run& r) { self->start_driving(r); },
                self
            );
        }
        else // красный — в очередь
        {
            road_.push(direction_, self);
            run.delete_active_event();
        }
    }

    void car::start_driving(runner::i_run& run)
    {
        auto self = shared_from_this();

        if (!road_.is_free())
        {
            // места нет — возвращаемся в начало очереди
            road_.push_front(direction_, self);
            run.delete_active_event();
            return;
        }

        // стартуем
        drive_start_time_ = run.model_time();
        std::cout << drive_start_time_ << ": car " << id_ << " started moving from " << direction_ << std::endl;
        road_.enter();

        run.move_active_event
        (
            road_.passage_time(),
            [self](runner::i_run& r) { self->finish_driving(r); }
        );

        // будим следующего через cars_interval
        auto next = road_.pop(direction_);
        if (!next) { return; }

        run.new_event
        (
            next,
            [next](runner::i_run& r) { next->start_driving(r); },
            run.model_time() + road_.cars_interval()
        );
    }

    void car::finish_driving(runner::i_run& run)
    {
        departure_time_ = run.model_time();
        std::cout << departure_time_ << ": car " << id_ << " left from " << direction_ << std::endl;
        road_.exit();

        // сразу будим следующего — место освободилось
        auto next = road_.pop(direction_);
        if (next)
        {
            run.new_event
            (
                next,
                [next](runner::i_run& r) { next->start_driving(r); },
                run.model_time()
            );
        }

        run.delete_active_event();
    }
}