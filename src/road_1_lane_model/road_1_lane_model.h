#pragma once

#include <memory>
#include <string>

#include "i_model.h"
#include "agents/car_generator.h"
#include "agents/traffic_light.h"
#include "resources/road_segment.h"
#include "rng.h"

class road_1_lane_model : public runner::i_model
{
public:
    struct config
    {
        explicit config(const std::string& path);

        double_t passage_time;
        double_t cars_interval;
        double_t t_green;
        double_t t_red;
        double_t lambda_a;
        double_t lambda_b;
        unsigned seed;
    };

    explicit road_1_lane_model(const config& cfg);

    void reset(runner::i_run& run) override;
    void stop(runner::i_run& run) override;
private:
    config config_;

    math::rng rng_;

    resources::road_segment road_segment_;
    std::shared_ptr<agents::traffic_light> traffic_light_;
    std::shared_ptr<agents::car_generator> car_generator_a_;
    std::shared_ptr<agents::car_generator> car_generator_b_;
};