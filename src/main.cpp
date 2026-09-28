#include <cstdlib>
#include <string>

#include "logger.h"
#include "stats_logger.h"
#include "road_1_lane_model/road_1_lane_model.h"
#include "simple_runner/simple_runner.h"

namespace
{
    const double_t RUN_TIME = 5000.0;

    // Анализатор вызываем после закрытия логгеров, чтобы файлы были дописаны.
    // Код возврата игнорируем: графики строятся отдельно от прогона модели,
    // и их отсутствие не должно ломать саму симуляцию.
    void analyze(const std::string& csv,
                 const std::string& charts,
                 const std::string& label)
    {
        const std::string command = std::string("python3 ../tools/analyze.py ") + csv
                                    + " --out " + charts + " --label " + label;
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

    // Блок повторов: все прогоны одной конфигурации с сидами seed, seed+1, ...,
    // один csv с колонкой replication 1..count, свой jsonl на каждый прогон.
    void run_repeated(const std::string& config,
                      const std::string& jsonl_dir,
                      const std::string& csv,
                      const std::string& charts,
                      const std::string& label,
                      const int count)
    {
        auto& logger = logging::logger::instance();
        auto& stats = logging::stats_logger::instance();

        stats.start(csv, 1);

        for (int rep = 1; rep <= count; ++rep)
        {
            logger.start(jsonl_dir + "_" + std::to_string(rep) + ".jsonl");

            road_1_lane_model::config cfg(config);
            cfg.seed += rep - 1;

            const auto model = std::make_shared<road_1_lane_model>(cfg);
            simple_runner runner(model, RUN_TIME);
            stats.set_replication(rep);
            runner.simulate();

            logger.close();
        }

        stats.close();

        analyze(csv, charts, label);
    }
}

int main()
{
    const std::string cfg = "../custom_configs/";
    const std::string out = "../results/";

    run_once(cfg + "01_low.json",          out + "01_low.jsonl",
             out + "01_low.csv",           out + "01_low_charts",
             "01_low");
    run_once(cfg + "02_base.json",         out + "02_base.jsonl",
             out + "02_base.csv",          out + "02_base_charts",
             "02_base");
    run_once(cfg + "03_mid.json",          out + "03_mid.jsonl",
             out + "03_mid.csv",           out + "03_mid_charts",
             "03_mid");
    run_once(cfg + "04_overload.json",     out + "04_overload.jsonl",
             out + "04_overload.csv",      out + "04_overload_charts",
             "04_overload");
    run_once(cfg + "05_heavy.json",        out + "05_heavy.jsonl",
             out + "05_heavy.csv",         out + "05_heavy_charts",
             "05_heavy");
    run_once(cfg + "06_a_heavy.json",      out + "06_a_heavy.jsonl",
             out + "06_a_heavy.csv",       out + "06_a_heavy_charts",
             "06_a_heavy");
    run_once(cfg + "07_b_heavy.json",      out + "07_b_heavy.jsonl",
             out + "07_b_heavy.csv",       out + "07_b_heavy_charts",
             "07_b_heavy");
    run_once(cfg + "08_short_green.json",  out + "08_short_green.jsonl",
             out + "08_short_green.csv",   out + "08_short_green_charts",
             "08_short_green");

    run_repeated(cfg + "10_reps_base.json",     out + "10_reps_base",
                 out + "10_reps_base.csv",      out + "10_reps_base_charts",
                 "10_reps_base", 8);
    run_repeated(cfg + "20_reps_overload.json", out + "20_reps_overload",
                 out + "20_reps_overload.csv",  out + "20_reps_overload_charts",
                 "20_reps_overload", 8);

    return 0;
}