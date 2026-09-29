#include <cstdio>
#include <cstdlib>
#include <string>
#include <vector>

#include "logger.h"
#include "stats_logger.h"
#include "road_1_lane_model/road_1_lane_model.h"
#include "simple_runner/simple_runner.h"

namespace
{
    const double_t RUN_TIME = 1200.0;

    void analyze(const std::string& csv,
                 const std::string& charts,
                 const std::string& label)
    {
        const std::string command = std::string("python3 ../tools/analyze.py ") + csv
                                    + " --out " + charts + " --label " + label;
        std::system(command.c_str());
    }

    void correlate(const std::vector<std::string>& csvs,
                   const std::vector<double_t>& lambdas,
                   const std::string& out_dir,
                   const std::string& label)
    {
        std::string files;
        for (const auto& csv : csvs)
        {
            if (!files.empty()) { files += " "; }
            files += csv;
        }

        std::string lambda_list;
        for (const auto lambda : lambdas)
        {
            if (!lambda_list.empty()) { lambda_list += ","; }
            char text[32];
            std::snprintf(text, sizeof(text), "%.10g", lambda);
            lambda_list += text;
        }

        const std::string command = std::string("python3 ../tools/correlate.py ") + files
                                    + " --lambdas " + lambda_list
                                    + " --out " + out_dir + " --label " + label;
        std::system(command.c_str());
    }

    // Один прогон: свои csv, jsonl и папка графиков.
    void run_once(const std::string& config,
                  const std::string& jsonl,
                  const std::string& csv,
                  const std::string& charts,
                  const std::string& label)
    {
        auto& logger = logging::logger::instance();
        auto& stats = logging::stats_logger::instance();

        logger.start(jsonl);
        stats.start(csv, 1);

        const auto model = std::make_shared<road_1_lane_model>(
            road_1_lane_model::config(config));
        simple_runner runner(model, RUN_TIME);
        runner.simulate();

        stats.close();
        logger.close();

        analyze(csv, charts, label);
    }

    void run_repeated(const road_1_lane_model::config& base_cfg,
                      const std::string& jsonl_dir,
                      const std::string& csv,
                      const std::string& charts,
                      const std::string& label,
                      const int count,
                      const bool draw_charts = true)
    {
        auto& logger = logging::logger::instance();
        auto& stats = logging::stats_logger::instance();

        stats.start(csv, 1);

        for (int rep = 1; rep <= count; ++rep)
        {
            logger.start(jsonl_dir + "_" + std::to_string(rep) + ".jsonl");

            auto cfg = base_cfg;
            cfg.seed += rep - 1;

            const auto model = std::make_shared<road_1_lane_model>(cfg);
            simple_runner runner(model, RUN_TIME);
            stats.set_replication(rep);
            runner.simulate();

            logger.close();
        }

        stats.close();

        if (draw_charts)
        {
            analyze(csv, charts, label);
        }
    }
}

int main()
{
    const std::string cfg = "../custom_configs/";
    const std::string out = "../results/";

    const std::string out_intensity = out + "09_intensity/";

    {
        const double_t lambda_min = 0.10;
        const double_t lambda_max = 0.60;
        const double_t lambda_step = 0.05;
        const int reps = 8;
        int level = 0;

        std::vector<std::string> csvs;
        std::vector<double_t> lambdas;
        for (double_t lambda = lambda_min; lambda <= lambda_max + 1e-9; lambda += lambda_step)
        {
            char label_text[32];
            std::snprintf(label_text, sizeof(label_text), "%.2f", lambda);
            const std::string label = std::string("09_intensity_") + label_text;

            const road_1_lane_model::config base_cfg(
                30.0, 1.0, 35.0, 50.0, lambda, lambda,
                static_cast<unsigned>(7777u));

            run_repeated(base_cfg,
                         out_intensity + label,
                         out_intensity + label + ".csv",
                         "", label, reps, false);

            csvs.push_back(out_intensity + label + ".csv");
            lambdas.push_back(lambda);
            ++level;
        }

        correlate(csvs, lambdas, out_intensity + "correlations", "09_intensity");
    }

    run_once(cfg + "06_a_heavy.json",      out + "06_a_heavy.jsonl",
             out + "06_a_heavy.csv",       out + "06_a_heavy_charts",
             "06_a_heavy");
    run_once(cfg + "07_b_heavy.json",      out + "07_b_heavy.jsonl",
             out + "07_b_heavy.csv",       out + "07_b_heavy_charts",
             "07_b_heavy");
    run_once(cfg + "08_short_green.json",  out + "08_short_green.jsonl",
             out + "08_short_green.csv",   out + "08_short_green_charts",
             "08_short_green");

    run_repeated(road_1_lane_model::config(cfg + "10_reps_base.json"),
                 out + "10_reps_base",
                 out + "10_reps_base.csv",
                 out + "10_reps_base_charts",
                 "10_reps_base", 8);
    run_repeated(road_1_lane_model::config(cfg + "20_reps_overload.json"),
                 out + "20_reps_overload",
                 out + "20_reps_overload.csv",
                 out + "20_reps_overload_charts",
                 "20_reps_overload", 8);

    return 0;
}