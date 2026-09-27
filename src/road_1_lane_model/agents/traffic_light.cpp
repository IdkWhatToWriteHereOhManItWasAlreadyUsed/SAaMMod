#include "traffic_light.h"
#include "road_1_lane_model/resources/road_segment.h"
#include "road_1_lane_model/agents/car.h"

namespace agents
{
    traffic_light::traffic_light(resources::road_segment& road,
                                 double_t t_green,
                                 double_t t_red)
        : road_(road)
        , t_green_(t_green)
        , t_red_(t_red)
        , phase_('A')
    {
    }

    int traffic_light::id() const { return 0; }

    char traffic_light::phase() const { return phase_; }

    void traffic_light::switch_to(runner::i_run& run, char direction)
    {
        phase_ = direction;
        wake_up_queue(run, direction);

        auto self = shared_from_this();
        run.move_active_event
        (
            t_green_,
            [self](runner::i_run& r) { self->switch_to_none(r); }
        );
    }

    void traffic_light::switch_to_none(runner::i_run& run)
    {
        const char previous = phase_;
        phase_ = 'N';

        char next = (previous == 'A') ? 'B' : 'A';

        auto self = shared_from_this();
        run.move_active_event
        (
            t_red_,
            [self, next](runner::i_run& r) { self->switch_to(r, next); }
        );
    }

    void traffic_light::wake_up_queue(runner::i_run& run, char direction)
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