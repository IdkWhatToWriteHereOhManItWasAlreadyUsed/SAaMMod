#include <filesystem>
#include <fstream>
#include <iostream>
#include <memory>
#include <string>

#include "stats_logger.h"
#include "interactive/console_control.h"
#include "interactive/interactive_runner.h"
#include "road_1_lane_model/road_1_lane_model.h"
#include "simple_runner/simple_runner.h"

namespace
{
    constexpr double_t RUN_TIME = 10000.0;

    // Пункт 1: варьирование t_green вокруг x0 из конфига, k = -4..4.
    constexpr int      LEVELS = 9;
    constexpr int      K_MIN  = -4;
    constexpr int      REPS   = 20;
    constexpr double_t DELTA  = 4.0;

    // Пункт 2: интерактивное изменение t_green.
    // Начальное состояние задаётся прямо в коде, без файла конфига.
    constexpr double_t INTERACTIVE_T_GREEN_START = 5.0;
    constexpr double_t INTERACTIVE_DELTA         = 5.0;
    constexpr double_t INTERACTIVE_INTERVAL      = 1000.0;
    constexpr double_t INTERACTIVE_RUN_TIME      = 66666.0;

    // Пункт 3: сравнение политик диспетчеризации.
    constexpr int DISPATCH_REPS = 20;

    const std::string CFG_DIR  = "../custom_configs/";
    const std::string OUT_DIR  = "../results/";
    const std::string LIVE_PLOT = "../tools/live_plot.py";

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

    // ---- пункт 3: сравнение политик диспетчеризации ----
    struct dispatch_variant
    {
        agents::dispatch_mode mode;
        const char* name;
    };

    void run_dispatch_set(const road_1_lane_model::config& base_cfg,
                          const std::string& out_dir)
    {
        const dispatch_variant variants[] =
        {
            {agents::dispatch_mode::fixed,     "fixed"},
            {agents::dispatch_mode::clearance, "clearance"},
            {agents::dispatch_mode::adaptive,  "adaptive"},
        };

        for (const dispatch_variant& variant : variants)
        {
            auto cfg = base_cfg;
            cfg.dispatch = variant.mode;
            run_pack(cfg, out_dir + "/" + variant.name,
                     DISPATCH_REPS, RUN_TIME);
        }
    }

    void run_dispatch_experiment(const std::string& out_dir)
    {
        // Симметричная нагрузка: адаптации почти нечего делать.
        const road_1_lane_model::config symmetric(
            20.0, 2.0, 60.0, 30.0, 0.11, 0.11, 1567778u);
        run_dispatch_set(symmetric, out_dir + "/symmetric");

        // Асимметричная нагрузка: здесь адаптивный зелёный должен дать
        // заметный эффект за счёт перераспределения времени в пользу A.
        const road_1_lane_model::config asymmetric(
            20.0, 2.0, 60.0, 30.0, 0.15, 0.07, 1567778u);
        run_dispatch_set(asymmetric, out_dir + "/asymmetric");
    }

    // ---- выбор режима запуска ----
    bool valid_mode(const std::string& mode)
    {
        return mode == "1" || mode == "2" || mode == "3" || mode == "all";
    }

    std::string trim(std::string text)
    {
        const std::string whitespace = " \t\r\n";
        const std::size_t begin = text.find_first_not_of(whitespace);
        if (begin == std::string::npos)
        {
            return {};
        }
        const std::size_t end = text.find_last_not_of(whitespace);
        return text.substr(begin, end - begin + 1);
    }

    // Аргумент командной строки имеет приоритет. Если аргументов нет,
    // спрашиваем пункт в консоли; неверный ввод повторяет вопрос.
    std::string choose_mode(const int argc, char** argv)
    {
        if (argc > 1)
        {
            return trim(argv[1]);
        }

        while (true)
        {
            std::cout
                << "\nВыберите пункт:\n"
                   "  1 — зависимость Y от t_green\n"
                   "  2 — интерактивный прогон t_green\n"
                   "  3 — сравнение fixed / clearance / adaptive\n"
                   "  all — все три пункта\n"
                   "Ввод: " << std::flush;

            std::string line;
            if (!std::getline(std::cin, line))
            {
                std::cerr << "\nввод закрыт\n";
                return {};
            }

            line = trim(line);
            if (valid_mode(line))
            {
                return line;
            }
            std::cout << "неверный выбор: '" << line << "'\n";
        }
    }

    // ---- пункт 2: интерактивное добавление ресурса ----
    // Раз в interval модельных секунд показывается график до текущего
    // момента и запрашивается новое значение параметра:
    //   Enter — текущее + delta, число — новое значение, q — конец прогона.
    void run_interactive(const road_1_lane_model::config& base_cfg,
                         const std::string& out_dir,
                         const std::string& parameter,
                         const double_t start,
                         const double_t delta,
                         const double_t interval,
                         const double_t run_time,
                         const std::string& script_path)
    {
        auto& stats = logging::stats_logger::instance();
        stats.summary_start(out_dir + "/ramp_summary.csv");
        stats.interval_start(out_dir + "/ramp_interval.csv", 10.0);
        stats.begin_run(0.0);

        auto model = std::make_shared<road_1_lane_model>(base_cfg);

        const std::string abs_out =
            std::filesystem::absolute(out_dir).string();
        auto control = std::make_shared<console_control>(
            *model,
            parameter,
            start,
            delta,
            interval,
            run_time,
            abs_out + "/ramp_interval.csv",
            std::filesystem::absolute(script_path).string(),
            abs_out + "/ramp_log.csv");

        interactive_runner runner(model, run_time, control);
        runner.simulate();

        stats.publish(1);
        stats.write_replication(1, base_cfg.seed, runner.actual_run_time());
        stats.summary_close();
        stats.interval_close();
    }
}

int main(const int argc, char** argv)
{
    // Режим: 1 — зависимость, 2 — интерактивный прогон,
    // 3 — сравнение политик, all — все три пункта.
    const std::string mode = choose_mode(argc, argv);
    if (!valid_mode(mode))
    {
        std::cerr << "использование: " << argv[0]
                  << " [1|2|3|all]\n";
        return 1;
    }

    if (mode == "1" || mode == "all")
    {
        run_tgreen_sweep(CFG_DIR + "lab3_base.json", OUT_DIR + "1_tgreen");
    }

    if (mode == "2" || mode == "all")
    {
        // Начальное состояние и шаг изменения задаются в коде.
        const road_1_lane_model::config interactive_cfg(
            20.0,                         // passage_time
            2.0,                          // cars_interval
            INTERACTIVE_T_GREEN_START,    // t_green
            30.0,                         // t_red
            0.11,                         // lambda_a
            0.11,                         // lambda_b
            1567778u);                    // seed

        run_interactive(interactive_cfg, OUT_DIR + "2_tgreen_interactive",
                        "t_green", INTERACTIVE_T_GREEN_START,
                        INTERACTIVE_DELTA, INTERACTIVE_INTERVAL,
                        INTERACTIVE_RUN_TIME, LIVE_PLOT);
    }

    if (mode == "3" || mode == "all")
    {
        run_dispatch_experiment(OUT_DIR + "3_dispatch");
    }

    return 0;
}
