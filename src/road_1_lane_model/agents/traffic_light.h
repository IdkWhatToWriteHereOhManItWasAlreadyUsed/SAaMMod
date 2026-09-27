#pragma once

#include <memory>

#include "i_agent.h"
#include "i_run.h"

namespace resources { class road_segment; }

namespace agents
{
    class traffic_light : public runner::i_agent,
                          public std::enable_shared_from_this<traffic_light>
    {
    public:
        traffic_light(resources::road_segment& road,
                      double_t t_green,
                      double_t t_red);
        int id() const override;
        char phase() const;
        void switch_to(runner::i_run& run, char direction);
        void switch_to_none(runner::i_run& run);
    private:
        void wake_up_queue(runner::i_run& run, char direction);
        resources::road_segment& road_;
        double_t t_green_;
        double_t t_red_;
        char phase_;
    };
}