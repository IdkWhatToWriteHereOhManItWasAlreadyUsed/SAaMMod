#pragma once

#include <memory>
#include <string>

#include "i_agent.h"
#include "i_run.h"

namespace resources { class road_segment; }
namespace agents { class traffic_light; }

namespace agents
{
    class car : public runner::i_agent,
                public std::enable_shared_from_this<car>
    {
    public:
        car(int id,
            char direction,
            resources::road_segment& road,
            agents::traffic_light& light);

        int id() const override;

        void arrive(runner::i_run& run);
        void start_driving(runner::i_run& run);
        void finish_driving(runner::i_run& run);
        
        char direction() const;
        double_t arrival_time() const;
        double_t drive_start_time() const;
        double_t departure_time() const;

    private:
        int id_;
        char direction_;
        resources::road_segment& road_;
        agents::traffic_light& light_;

        double_t arrival_time_ = 0;
        double_t drive_start_time_ = 0;
        double_t departure_time_ = 0;
    };
}