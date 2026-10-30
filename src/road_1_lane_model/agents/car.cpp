#include "car.h"

#include <iostream>                       // ← DBG
#include "logger.h"
#include "stats_logger.h"
#include "road_1_lane_model/resources/road_segment.h"
#include "road_1_lane_model/agents/traffic_light.h"

namespace agents
{
    car::car(const int id,
             const char direction,
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
    bool car::is_waiting_slot() const { return waiting_slot_; }
    void car::set_waiting_slot(const bool value) { waiting_slot_ = value; }

    void car::arrive(runner::i_run& run)
    {
        arrival_time_ = run.model_time();
        logging::logger::instance().write_car(arrival_time_, id_, "arrive", direction_);


        auto self = shared_from_this();

        if (light_.phase() == direction_ && road_.queue_empty(direction_))
        {
            run.next_active_event
            (
                [self](runner::i_run& r) { self->start_driving(r); },
                self
            );
        }
        else
        {
            road_.push(direction_, self);
            run.delete_active_event();
        }
    }

    void car::start_driving(runner::i_run& run)
    {
        auto self = shared_from_this();

        road_.attach(direction_, self);

        if (!road_.is_free() || light_.phase() != direction_)
        {
            road_.push_front(direction_, self);
            run.delete_active_event();
            return;
        }

        drive_start_time_ = run.model_time();

        if (auto interval = drive_start_time_ - road_.last_car_enter_time();
            interval < road_.cars_interval())
        {
            const double_t wait = road_.last_car_enter_time() + road_.cars_interval() - drive_start_time_;

            if (road_.queue_empty(direction_))
            {
                if (wait <= 1e-9)
                {
                }
                else
                {
                    road_.detach(direction_, self);
                    run.move_active_event
                    (
                        wait,
                        [self](runner::i_run& r) { self->start_driving(r); }
                    );
                    return;
                }
            }
            else
            {
                road_.push_front(direction_, self);
                run.delete_active_event();
                return;
            }
        }


        logging::stats_logger::instance().car_waited(drive_start_time_ - arrival_time_);
        logging::logger::instance().write_car(drive_start_time_, id_, "enter", direction_);
        road_.enter(drive_start_time_);

        run.move_active_event
        (
            road_.passage_time(),
            [self](runner::i_run& r) { self->finish_driving(r); }
        );

        auto next = road_.pop(direction_);
        if (!next)
        {
            return;
        }

        road_.detach(direction_, next);

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
        logging::logger::instance().write_car(departure_time_, id_, "leave", direction_);
        logging::stats_logger::instance().car_passed(departure_time_ - arrival_time_);
        road_.exit();


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