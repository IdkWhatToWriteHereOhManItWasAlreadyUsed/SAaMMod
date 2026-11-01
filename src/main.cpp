#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <memory>
#include <string>

#include "stats_logger.h"
#include "road_1_lane_model/road_1_lane_model.h"
#include "simple_runner/simple_runner.h"

namespace
{
    constexpr double_t RUN_TIME = 6000.0;
    const std::string CFG_DIR = "../custom_configs/";
    const std::string OUT_DIR = "../results/";

    enum class param { passage_time, cars_interval, t_green, t_red, lambda_a, lambda_b };

    double_t& field(road_1_lane_model::config& c, param p)
    {
        switch (p)
        {
            case param::passage_time:  return c.passage_time;
            case param::cars_interval: return c.cars_interval;
            case param::t_green:       return c.t_green;
            case param::t_red:         return c.t_red;
            case param::lambda_a:      return c.lambda_a;
            case param::lambda_b:      return c.lambda_b;
        }
        return c.lambda_a;
    }

    const char* name_of(param p)
    {
        switch (p)
        {
            case param::passage_time:  return "passage_time";
            case param::cars_interval: return "cars_interval";
            case param::t_green:       return "t_green";
            case param::t_red:         return "t_red";
            case param::lambda_a:      return "lambda_a";
            case param::lambda_b:      return "lambda_b";
        }
        return "lambda_a";
    }

    // ---- ЛР3: пакет реплик ----
    void run_lab3_pack(const road_1_lane_model::config& base_cfg,
                       const std::string& out_prefix,
                       const int count,
                       const double_t run_time)
    {
        auto& stats = logging::stats_logger::instance();
        stats.summary_start(out_prefix + "_summary.csv");

        for (int rep = 1; rep <= count; ++rep)
        {
            auto cfg = base_cfg;
            cfg.seed = base_cfg.seed + static_cast<unsigned>(rep - 1);

            stats.begin_run(0.0);

            auto model = std::make_shared<road_1_lane_model>(cfg);
            simple_runner runner(model, run_time);
            runner.simulate();

            stats.write_replication(rep, cfg.seed, run_time);
        }
        stats.summary_close();
    }

    void run_lab3_pack(const std::string& config_path,
                       const std::string& out_prefix,
                       const int count,
                       const double_t run_time)
    {
        run_lab3_pack(road_1_lane_model::config(config_path),
                      out_prefix, count, run_time);
    }

    // ---- ЛР3 п.1.3: зависимость точности от n ----
    void run_lab3_precision(const std::string& config_path,
                            const std::string& out_dir)
    {
        const int ns[] = {5, 10, 20, 30, 50, 100, 150, 200};
        for (int n : ns)
        {
            const std::string prefix = out_dir + "/n" + std::to_string(n);
            run_lab3_pack(config_path, prefix, n, RUN_TIME);
        }
    }

    // ---- ЛР3 п.1.4: переходный период ----
    void run_lab3_transient(const std::string& config_path,
                            const std::string& out_dir,
                            const double_t long_run_time,
                            const int repl)
    {
        auto& stats = logging::stats_logger::instance();
        stats.interval_start(out_dir + "/transient_interval.csv", 10.0);

        const road_1_lane_model::config base_cfg(config_path);

        for (int rep = 1; rep <= repl; ++rep)
        {
            auto cfg = base_cfg;
            cfg.seed = base_cfg.seed + static_cast<unsigned>(rep - 1);

            stats.set_interval_rep(rep);
            stats.begin_run(0.0);

            auto model = std::make_shared<road_1_lane_model>(cfg);
            simple_runner runner(model, long_run_time);
            runner.simulate();
        }

        stats.interval_close();
    }

    // ---- ЛР3 п.1.5: возможность непрерывного прогона (через автокорреляцию реплик) ----
    void run_lab3_continuous(const std::string& config_path,
                             const std::string& out_dir,
                             const double_t run_time,
                             const int repl)
    {
        run_lab3_pack(config_path, out_dir + "/continuous", repl, run_time);
    }

    // ---- ЛР3 п.1.6: чувствительность к произвольному параметру ----
    // points = 5 (k = -2..2), window = reps_per_point
    void run_lab3_sensitivity(const std::string& config_path,
                              const std::string& out_dir,
                              param p,
                              const double_t x0,
                              const double_t delta,
                              const int reps_per_point)
    {
        auto base_cfg = road_1_lane_model::config(config_path);
        const std::string tag = name_of(p);

        for (int k = -2; k <= 2; ++k)
        {
            auto cfg = base_cfg;
            field(cfg, p) = x0 + k * delta;

            const std::string prefix = out_dir + "/" + tag + "_x" + std::to_string(k);
            run_lab3_pack(cfg, prefix, reps_per_point, RUN_TIME);
        }
    }
}

int main()
{
    const std::string base_cfg = CFG_DIR + "lab3_base.json";
    const std::string base_out = OUT_DIR + "lab3_base";

    run_lab3_pack(base_cfg, base_out + "_n180", 180, RUN_TIME);
    run_lab3_pack(base_cfg, base_out + "_n20",  20,  RUN_TIME);

    run_lab3_precision  (base_cfg, OUT_DIR + "lab3_precision");
    run_lab3_transient  (base_cfg, OUT_DIR + "lab3_transient", 6000.0, 10);
    run_lab3_continuous (base_cfg, OUT_DIR + "lab3_continuous", RUN_TIME, 30);

    // по lambda_a: x0 = 0.08, delta = 0.01, 5 реплик на точку
    run_lab3_sensitivity(base_cfg, OUT_DIR + "lab3_sensitivity",
                         param::lambda_a, 0.08, 0.01, 5);

    // примеры других параметров:
    // run_lab3_sensitivity(base_cfg, OUT_DIR + "lab3_sens_tgreen",
    //                      param::t_green, 60.0, 5.0, 5);
    // run_lab3_sensitivity(base_cfg, OUT_DIR + "lab3_sens_passage",
    //                      param::passage_time, 20.0, 2.0, 5);

    return 0;
}