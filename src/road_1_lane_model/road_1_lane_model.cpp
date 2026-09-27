#include "road_1_lane_model.h"

#include <fstream>
#include <stdexcept>
#include <iostream>
#include <json/json.h>

road_1_lane_model::config::config(const std::string& path)
{
    std::ifstream file(path);
    if (!file.is_open())
    {
        throw std::runtime_error("cannot open config: " + path);
    }

    Json::Value root;
    Json::CharReaderBuilder builder;
    std::string errors;

    if (!Json::parseFromStream(builder, file, &root, &errors))
    {
        throw std::runtime_error("cannot parse config: " + errors);
    }

    passage_time  = root["passage_time"].asDouble();
    cars_interval = root["cars_interval"].asDouble();
    t_green       = root["t_green"].asDouble();
    t_red         = root["t_red"].asDouble();
    lambda_a      = root["lambda_a"].asDouble();
    lambda_b      = root["lambda_b"].asDouble();
    seed          = root["seed"].asUInt();
}

road_1_lane_model::road_1_lane_model(const config& cfg)
    : config_(cfg)
    , rng_(cfg.seed)
    , road_segment_(cfg.passage_time, cfg.cars_interval)
    , traffic_light_(std::make_shared<agents::traffic_light>(
          road_segment_, cfg.t_green, cfg.t_red))
{
    car_generator_a_ = std::make_shared<agents::car_generator>(
        'A', cfg.lambda_a, rng_, road_segment_, *traffic_light_);

    car_generator_b_ = std::make_shared<agents::car_generator>(
        'B', cfg.lambda_b, rng_, road_segment_, *traffic_light_);
}

void road_1_lane_model::reset(runner::i_run& run)
{
    run.new_event
    (
        traffic_light_,
        [this](runner::i_run& r) { traffic_light_->switch_to(r, 'A'); },
        0.0
    );

    run.new_event
    (
        car_generator_a_,
        [this](runner::i_run& r) { car_generator_a_->spawn_car(r); },
        rng_.exponential(config_.lambda_a)
    );

    run.new_event
    (
        car_generator_b_,
        [this](runner::i_run& r) { car_generator_b_->spawn_car(r); },
        rng_.exponential(config_.lambda_b)
    );
}

void road_1_lane_model::stop(runner::i_run& run)
{
    run.delete_event(car_generator_a_);
    run.delete_event(car_generator_b_);
}
