#include <filesystem>
#include <fstream>
#include <memory>
#include <string>

#include "stats_logger.h"
#include "road_1_lane_model/road_1_lane_model.h"
#include "simple_runner/simple_runner.h"

namespace
{
    constexpr double_t RUN_TIME = 10000.0;

    // Пункт 1: варьирование t_green вокруг x0 из конфига, k = -4..4.
    constexpr int      LEVELS = 9;
    constexpr int      K_MIN  = -4;
    constexpr int      REPS   = 20;
    constexpr double_t DELTA  = 8.0;

    // Пункт 2: начальное состояние и рантайм-изменение t_green.
    // Начальное состояние задаётся прямо в коде, без файла конфига.
    constexpr double_t RAMP_T_GREEN_START    = 1.0;
    constexpr double_t RAMP_T_GREEN_STEP     = 0.5;
    constexpr double_t RAMP_T_GREEN_INTERVAL = 100.0;
    constexpr double_t RAMP_RUN_TIME         = 33333.0;

    const std::string CFG_DIR = "../custom_configs/";
    const std::string OUT_DIR = "../results/";

    // ---- последовательный пакет реплик ----
    void run_pack(const road_1_lane_model::config& base_cfg,
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

            stats.publish(rep);
            stats.write_replication(rep, cfg.seed, run_time);
        }

        stats.summary_close();
    }

    // ---- пункт 1: зависимость отклика от t_green ----
    void run_tgreen_sweep(const std::string& config_path,
                          const std::string& out_dir)
    {
        std::filesystem::create_directories(out_dir);

        const road_1_lane_model::config base_cfg(config_path);
        const double_t x0 = base_cfg.t_green;

        for (int k = K_MIN; k < K_MIN + LEVELS; ++k)
        {
            auto cfg = base_cfg;
            cfg.t_green = x0 + k * DELTA;

            const std::string prefix =
                out_dir + "/tgreen_x" + std::to_string(k);
            run_pack(cfg, prefix, REPS, RUN_TIME);
        }

        std::ofstream meta(out_dir + "/meta.csv");
        meta << "variable,x0,delta,levels,k_min,k_max,reps_per_level,"
                "run_time,seed\n"
             << "t_green," << x0 << ',' << DELTA << ',' << LEVELS << ','
             << K_MIN << ',' << K_MIN + LEVELS - 1 << ',' << REPS << ','
             << RUN_TIME << ',' << base_cfg.seed << '\n';
    }

    // ---- пункт 2: изменение параметра в рантайме ----
    // Передаём имя параметра, начальное значение, шаг и интервал изменения.
    // Первое значение применяется в t=0, далее каждые interval модельных
    // секунд параметр меняется на step, пока не достигнуто run_time.
    void run_parameter_ramp(const road_1_lane_model::config& base_cfg,
                            const std::string& out_dir,
                            const std::string& parameter,
                            const double_t start,
                            const double_t step,
                            const double_t interval,
                            const double_t run_time)
    {
        auto& stats = logging::stats_logger::instance();
        stats.summary_start(out_dir + "/ramp_summary.csv");
        stats.interval_start(out_dir + "/ramp_interval.csv", 10.0);
        stats.begin_run(0.0);

        auto model = std::make_shared<road_1_lane_model>(base_cfg);
        model->add_parameter_ramp(parameter, start, step, interval, run_time,
                                  out_dir + "/ramp_log.csv");

        simple_runner runner(model, run_time);
        runner.simulate();

        stats.publish(1);
        stats.write_replication(1, base_cfg.seed, run_time);
        stats.summary_close();
        stats.interval_close();
    }
}

int main()
{
    // Пункт 1: 9 уровней t_green по 20 реплик.
    run_tgreen_sweep(CFG_DIR + "lab3_base.json", OUT_DIR + "1_tgreen");

    // Пункт 2: начальное состояние и изменение t_green задаются в коде.
    const road_1_lane_model::config ramp_cfg (
        20.0,                    // passage_time
        2.0,                     // cars_interval
        RAMP_T_GREEN_START,      // t_green
        30.0,                    // t_red
        0.11,                    // lambda_a
        0.11,                    // lambda_b
        666777
        );               // seed

    run_parameter_ramp(ramp_cfg, OUT_DIR + "2_tgreen_ramp",
                       "t_green", RAMP_T_GREEN_START,
                       RAMP_T_GREEN_STEP, RAMP_T_GREEN_INTERVAL,
                       RAMP_RUN_TIME);

    return 0;
}
