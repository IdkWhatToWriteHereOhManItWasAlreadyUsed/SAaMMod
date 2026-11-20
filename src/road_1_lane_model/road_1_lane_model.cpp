#include "road_1_lane_model.h"

#include <cmath>
#include <fstream>
#include <stdexcept>
#include <iostream>
#include <json/json.h>

#include "stats_logger.h"

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

    const std::string dispatch_name =
        root.get("dispatch", "fixed").asString();
    if (dispatch_name == "clearance")
    {
        this->dispatch = agents::dispatch_mode::clearance;
    }
    else if (dispatch_name == "adaptive")
    {
        this->dispatch = agents::dispatch_mode::adaptive;
    }
    else if (dispatch_name == "fixed")
    {
        this->dispatch = agents::dispatch_mode::fixed;
    }
    else
    {
        throw std::runtime_error("unknown dispatch mode: " + dispatch_name);
    }
}

road_1_lane_model::road_1_lane_model(const config& cfg)
    : config_(cfg)
    , rng_(cfg.seed)
    , road_segment_(cfg.passage_time, cfg.cars_interval)
    , traffic_light_(std::make_shared<agents::traffic_light>(
          road_segment_, cfg.t_green, cfg.t_red, cfg.dispatch))
{
    car_generator_a_ = std::make_shared<agents::car_generator>(
        'A', cfg.lambda_a, rng_, road_segment_, *traffic_light_);

    car_generator_b_ = std::make_shared<agents::car_generator>(
        'B', cfg.lambda_b, rng_, road_segment_, *traffic_light_);
}

void road_1_lane_model::reset(runner::i_run& run)
{
    road_segment_.reset();
    logging::stats_logger::instance().begin_run(run.model_time());

    run.new_event
    (
        traffic_light_,
        [this](runner::i_run& r) { traffic_light_->switch_to(r, 'A'); },
        0.0
    );

    run.new_event
    (
        car_generator_b_,
        [this](runner::i_run& r) { car_generator_b_->spawn_car(r); },
        rng_.exponential(config_.lambda_b)
    );

    run.new_event
    (
        car_generator_a_,
        [this](runner::i_run& r) { car_generator_a_->spawn_car(r); },
        rng_.exponential(config_.lambda_a)
    );

    for (const auto& ramp : ramps_)
    {
        ramp->start(run);
    }
}

bool road_1_lane_model::set_parameter(const std::string_view name,
                                      const double_t value)
{
    if (!std::isfinite(value) || value <= 0.0)
    {
        return false;
    }

    if (name == "passage_time")
    {
        config_.passage_time = value;
        road_segment_.set_passage_time(value);
        return true;
    }
    if (name == "cars_interval")
    {
        config_.cars_interval = value;
        road_segment_.set_cars_interval(value);
        return true;
    }
    if (name == "t_green")
    {
        config_.t_green = value;
        traffic_light_->set_t_green(value);
        return true;
    }
    if (name == "t_red")
    {
        config_.t_red = value;
        traffic_light_->set_t_red(value);
        return true;
    }
    if (name == "lambda_a")
    {
        config_.lambda_a = value;
        car_generator_a_->set_frequency(value);
        return true;
    }
    if (name == "lambda_b")
    {
        config_.lambda_b = value;
        car_generator_b_->set_frequency(value);
        return true;
    }

    return false;
}

void road_1_lane_model::add_parameter_ramp(const std::string& parameter,
                                           const double_t start,
                                           const double_t step,
                                           const double_t interval,
                                           const double_t until,
                                           const std::string& log_path)
{
    ramps_.push_back(std::make_shared<runner::parameter_ramp>(
        *this, parameter, start, step, interval, until, log_path));
}

void road_1_lane_model::stop(runner::i_run& run)
{
    run.delete_event(traffic_light_);
    run.delete_event(car_generator_a_);
    run.delete_event(car_generator_b_);
}

void road_1_lane_model::sample(runner::i_run& run)
{
    logging::stats_logger::instance().sample
    (
        run.model_time(),
        road_segment_.queue_size('A'),
        road_segment_.queue_size('B')
    );
}
