#include "car_generator.h"
#include "road_1_lane_model/resources/road_segment.h"
#include "road_1_lane_model/agents/traffic_light.h"
#include "road_1_lane_model/agents/car.h"

namespace agents
{
    car_generator::car_generator(char direction,
                                 double_t frequency,
                                 math::rng& rng,
                                 resources::road_segment& road,
                                 agents::traffic_light& light)
        : direction_(direction)
        , frequency_(frequency)
        , rng_(rng)
        , road_(road)
        , traffic_light_(light)
    {
    }

    int car_generator::id() const { return 0; }

    void car_generator::spawn_car(runner::i_run& run)
    {
        static int next_id = 0;

        auto self = shared_from_this();
        run.move_active_event
        (
            rng_.exponential(frequency_),
            [self](runner::i_run& r) { self->spawn_car(r); }
        );

        auto car = std::make_shared<agents::car>(next_id++, direction_, road_, traffic_light_);

        run.new_event
        (
            car,
            [car](runner::i_run& r) { car->arrive(r); },
            run.model_time()
        );
    }
}