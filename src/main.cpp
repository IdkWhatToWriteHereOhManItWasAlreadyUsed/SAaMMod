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
    constexpr double_t RUN_TIME = 1200.0;
    const std::string CFG_DIR = "../custom_configs/";
    const std::string OUT_DIR = "../results/";

    void run_lab3_pack(const std::string& config_path,
                       const std::string& out_prefix,
                       const int count,
                       const double_t run_time)
    {
        auto& stats = logging::stats_logger::instance();

        stats.summary_start(out_prefix + "_summary.csv");

        const road_1_lane_model::config base_cfg(config_path);

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

    void run_lab3_precision(const std::string& config_path,
                            const std::string& out_dir)
    {
        (void)config_path; (void)out_dir;
    }

    void run_lab3_transient(const std::string& config_path,
                            const std::string& out_dir,
                            const double_t long_run_time,
                            const int repl)
    {
        (void)config_path; (void)out_dir; (void)long_run_time; (void)repl;
    }

    void run_lab3_continuous(const std::string& config_path,
                             const std::string& out_dir,
                             const double_t run_time,
                             const int repl)
    {
        (void)config_path; (void)out_dir; (void)run_time; (void)repl;
    }

    void run_lab3_sensitivity(const std::string& config_path,
                              const std::string& out_dir,
                              const double_t x0,
                              const double_t delta,
                              const int reps_per_point)
    {
        (void)config_path; (void)out_dir; (void)x0; (void)delta; (void)reps_per_point;
    }
}

int main()
{
    const std::string base_cfg = CFG_DIR + "lab3_base.json";
    const std::string base_out = OUT_DIR + "lab3_base";

    //run_lab3_pack(base_cfg, base_out + "_n180", 180, RUN_TIME);
    run_lab3_pack(base_cfg, base_out + "_n20",  20,  RUN_TIME);

    run_lab3_precision  (base_cfg, OUT_DIR + "lab3_precision");
    run_lab3_transient  (base_cfg, OUT_DIR + "lab3_transient", 6000.0, 10);
    run_lab3_continuous (base_cfg, OUT_DIR + "lab3_continuous", RUN_TIME, 20);
    run_lab3_sensitivity(base_cfg, OUT_DIR + "lab3_sensitivity", 0.20, 0.02, 5);

    return 0;
}