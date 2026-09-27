#pragma once

#include <memory>

#include "i_agent.h"
#include "i_run.h"
#include "rng.h"

namespace resources { class road_segment; }
namespace agents { class traffic_light; class car; }

namespace agents
{
    class car_generator : public runner::i_agent,
                          public std::enable_shared_from_this<car_generator>
    {
    public:
        car_generator(char direction,
                      double_t frequency,
                      math::rng& rng,
                      resources::road_segment& road,
                      agents::traffic_light& light);
        int id() const override;
        void spawn_car(runner::i_run& run);
    private:
        char direction_;
        double_t frequency_;
        math::rng& rng_;
        resources::road_segment& road_;
        agents::traffic_light& traffic_light_;
    };
}