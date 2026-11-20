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
    constexpr int      REPS   = 30;
    constexpr double_t DELTA  = 4.0;

    // Пункт 2: интерактивное изменение t_green.
    // Начальное состояние задаётся прямо в коде, без файла конфига.
    constexpr double_t INTERACTIVE_T_GREEN_START = 5.0;
    constexpr double_t INTERACTIVE_DELTA         = 5.0;
    constexpr double_t INTERACTIVE_INTERVAL      = 1000.0;
    constexpr double_t INTERACTIVE_RUN_TIME      = 66666.0;

    // Пункт 3: сравнение политик диспетчеризации.
    constexpr int DISPATCH_REPS = 30;

    // Пункт 4: двухфакторный эксперимент по t_green и t_red.
    constexpr int TWO_FACTOR_REPS = 20;

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
        // Симметричная нагрузка near capacity: fixed уже на грани,
        // clearance/adaptive должны показать разницу.
        const road_1_lane_model::config symmetric(
            20.0, 2.0, 40.0, 25.0, 0.14, 0.14, 666777u);
        run_dispatch_set(symmetric, out_dir + "/symmetric");

        // Асимметричная нагрузка near capacity: A перегружено,
        // adaptive должен перераспределить зелёное в его пользу.
        const road_1_lane_model::config asymmetric(
            20.0, 2.0, 40.0, 25.0, 0.17, 0.09, 666777u);
        run_dispatch_set(asymmetric, out_dir + "/asymmetric");
    }

    // ---- пункт 4: двухфакторный эксперимент ----
    // Меняются только t_green и t_red, 5 уровней на каждый фактор.
    constexpr double_t TF_GREEN_LEVELS[] = {5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 45.0, 60.0, 75.0, 90.0, 100.0};
    constexpr double_t TF_RED_LEVELS[]   = {20.0, 30.0, 40.0, 50.0, 60.0};

    // Имя папки уровня без точки: 30 -> "30", 12.5 -> "12p5".
    std::string level_tag(const double_t value)
    {
        std::string text = std::to_string(static_cast<int>(value));
        return text;
    }

    void run_two_factor_set(const road_1_lane_model::config& base_cfg,
                            const std::string& out_dir)
    {
        std::filesystem::create_directories(out_dir);

        for (const double_t t_green : TF_GREEN_LEVELS)
        {
            for (const double_t t_red : TF_RED_LEVELS)
            {
                auto cfg = base_cfg;
                cfg.t_green = t_green;
                cfg.t_red = t_red;
                // Пункт 4 оценивает саму модель, политику не меняем.
                cfg.dispatch = agents::dispatch_mode::fixed;

                std::cout << "пункт 4: t_green=" << t_green
                          << ", t_red=" << t_red << '\n';

                const std::string prefix =
                    out_dir + "/g" + level_tag(t_green) +
                    "_r" + level_tag(t_red);
                run_pack(cfg, prefix, TWO_FACTOR_REPS, RUN_TIME);
            }
        }

        std::ofstream meta(out_dir + "/meta.csv");
        meta << "factor_x,levels_x,factor_y,levels_y,reps_per_point,"
                "run_time,seed\n";
        meta << "t_green,[";
        for (std::size_t i = 0; i < std::size(TF_GREEN_LEVELS); ++i)
        {
            meta << (i ? ";" : "") << TF_GREEN_LEVELS[i];
        }
        meta << "],t_red,[";
        for (std::size_t i = 0; i < std::size(TF_RED_LEVELS); ++i)
        {
            meta << (i ? ";" : "") << TF_RED_LEVELS[i];
        }
        meta << "]," << TWO_FACTOR_REPS << ',' << RUN_TIME << ','
             << base_cfg.seed << '\n';
    }

    void run_two_factor_experiment(const std::string& out_dir)
    {
        // Симметричная нагрузка.
        const road_1_lane_model::config symmetric(
            19.0, 2.0, 40.0, 25.0, 0.11, 0.11, 666777u);
        run_two_factor_set(symmetric, out_dir + "/symmetric");

        // Асимметричная нагрузка — для наглядности.
        const road_1_lane_model::config asymmetric(
            19.0, 2.0, 40.0, 25.0, 0.16, 0.097, 666777u);
       // run_two_factor_set(asymmetric, out_dir + "/asymmetric");
    }

    // ---- выбор режима запуска ----
    bool valid_mode(const std::string& mode)
    {
        return mode == "1" || mode == "2" || mode == "3" ||
               mode == "4" || mode == "all";
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
                   "  4 — двухфакторный эксперимент t_green × t_red\n"
                   "  all — все пункты\n"
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
    // 3 — сравнение политик, 4 — двухфакторный эксперимент,
    // all — все пункты.
    const std::string mode = choose_mode(argc, argv);
    if (!valid_mode(mode))
    {
        std::cerr << "использование: " << argv[0]
                  << " [1|2|3|4|all]\n";
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
            666777u);                    // seed

        run_interactive(interactive_cfg, OUT_DIR + "2_tgreen_interactive",
                        "t_green", INTERACTIVE_T_GREEN_START,
                        INTERACTIVE_DELTA, INTERACTIVE_INTERVAL,
                        INTERACTIVE_RUN_TIME, LIVE_PLOT);
    }

    if (mode == "3" || mode == "all")
    {
        run_dispatch_experiment(OUT_DIR + "3_dispatch");
    }

    if (mode == "4" || mode == "all")
    {
        run_two_factor_experiment(OUT_DIR + "4_two_factor");
    }

    return 0;
}
