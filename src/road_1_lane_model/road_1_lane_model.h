#pragma once

#include <memory>
#include <string>
#include <string_view>
#include <vector>

#include "i_model.h"
#include "parameter_ramp.h"
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

        config(double_t passage_time,
               double_t cars_interval,
               double_t t_green,
               double_t t_red,
               double_t lambda_a,
               double_t lambda_b,
               unsigned seed)
            : passage_time(passage_time)
            , cars_interval(cars_interval)
            , t_green(t_green)
            , t_red(t_red)
            , lambda_a(lambda_a)
            , lambda_b(lambda_b)
            , seed(seed)
        {
        }

        double_t passage_time;
        double_t cars_interval;
        double_t t_green;
        double_t t_red;
        double_t lambda_a;
        double_t lambda_b;
        mutable unsigned seed;

        // Политика диспетчеризации светофора. По умолчанию — прежнее
        // фиксированное поведение.
        agents::dispatch_mode dispatch = agents::dispatch_mode::fixed;
    };

    explicit road_1_lane_model(const config& cfg);

    void reset(runner::i_run& run) override;
    void stop(runner::i_run& run) override;
    void sample(runner::i_run& run) override;

    // Изменение параметра во время прогона: passage_time, cars_interval,
    // t_green, t_red, lambda_a, lambda_b.
    bool set_parameter(std::string_view name, double_t value) override;

    // Запланировать линейное изменение параметра по модельному времени.
    // log_path — необязательный csv-журнал изменений.
    void add_parameter_ramp(const std::string& parameter,
                            double_t start,
                            double_t step,
                            double_t interval,
                            double_t until,
                            const std::string& log_path = {});
private:
    config config_;

    math::rng rng_;

    resources::road_segment road_segment_;
    std::shared_ptr<agents::traffic_light> traffic_light_;
    std::shared_ptr<agents::car_generator> car_generator_a_;
    std::shared_ptr<agents::car_generator> car_generator_b_;
    std::vector<std::shared_ptr<runner::parameter_ramp>> ramps_;
};