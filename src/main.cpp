#include <algorithm>
#include <atomic>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <functional>
#include <iostream>
#include <memory>
#include <string>
#include <thread>
#include <vector>

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

    // ---- параллельный запуск реплик ----
    // каждая реплика независима (свой seed, своё thread-local ядро
    // статистики), поэтому реплики #1..count распределяются по пулу
    // потоков; ограничение по числу ядер, максимум 8
    void parallel_reps(int count, const std::function<void(int rep)>& job)
    {
        const unsigned hw = std::thread::hardware_concurrency();
        const std::size_t threads =
            std::max(1u, std::min<unsigned>(hw ? hw : 1u, 8u));

        std::atomic<int> next{1};
        std::vector<std::thread> pool;
        pool.reserve(std::min<std::size_t>(threads, count));
        for (std::size_t i = 0;
             i < threads && static_cast<int>(i) < count; ++i)
        {
            pool.emplace_back([&]
            {
                for (int rep = next.fetch_add(1);
                     rep <= count; rep = next.fetch_add(1))
                {
                    job(rep);
                }
            });
        }
        for (std::thread& t : pool) { t.join(); }
    }

    // ---- ЛР3: пакет реплик ----
    void run_lab3_pack(const road_1_lane_model::config& base_cfg,
                       const std::string& out_prefix,
                       const int count,
                       const double_t run_time)
    {
        auto& stats = logging::stats_logger::instance();
        stats.summary_start(out_prefix + "_summary.csv");

        parallel_reps(count, [&](int rep)
        {
            auto cfg = base_cfg;
            cfg.seed = base_cfg.seed + static_cast<unsigned>(rep - 1);

            stats.begin_run(0.0);

            auto model = std::make_shared<road_1_lane_model>(cfg);
            simple_runner runner(model, run_time);
            runner.simulate();

            stats.publish(rep);
        });

        // строки сводки пишутся последовательно в порядке реплик
        for (int rep = 1; rep <= count; ++rep)
        {
            stats.write_replication(
                rep, base_cfg.seed + static_cast<unsigned>(rep - 1), run_time);
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
    // реплики временных рядов выполняются параллельно; каждая реплика
    // копит строки интервала в thread-local буфер и публикует их в файл
    // одним блоком (порядок строк внутри реплики сохраняется)
    void run_lab3_transient(const std::string& config_path,
                            const std::string& out_dir,
                            const double_t long_run_time,
                            const int repl)
    {
        auto& stats = logging::stats_logger::instance();
        stats.interval_start(out_dir + "/transient_interval.csv", 10.0);

        const road_1_lane_model::config base_cfg(config_path);

        parallel_reps(repl, [&](int rep)
        {
            auto cfg = base_cfg;
            cfg.seed = base_cfg.seed + static_cast<unsigned>(rep - 1);

            stats.set_interval_rep(rep);
            stats.begin_run(0.0);

            auto model = std::make_shared<road_1_lane_model>(cfg);
            simple_runner runner(model, long_run_time);
            runner.simulate();

            stats.publish(rep);
        });

        stats.interval_close();
    }

    // ---- ЛР3 п.1.4: гипотеза об уменьшении времени прогона ----
    // серия опытов с одинаковым начальным состоянием и числом реплик,
    // но разными интервалами реализации реплик; {Y0} при T0 — эталон
    void run_lab3_shortened(const std::string& config_path,
                            const std::string& out_dir,
                            const int repl)
    {
        const double_t ts[] = {6000.0, 5000.0, 4000.0, 3000.0, 2400.0, 2000.0,
                               1800.0, 1700, 1500.0, 1400, 1300, 1200.0, 1100, 1000,  900.0, 800, 700, 600.0};
        for (const double_t t : ts)
        {
            const std::string prefix = out_dir + "/T" + std::to_string(static_cast<int>(t));
            run_lab3_pack(config_path, prefix, repl, t);
        }
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
    // x0 берётся ИЗ ТЕКУЩЕГО конфига (не рассинхронизируется при правках
    // конфигурации), точки x0 + k*delta, k = -3..3; рядом с данными
    // пишется meta.csv — им пользуется анализ lab3_stats.py
    void run_lab3_sensitivity(const std::string& config_path,
                              const std::string& out_dir,
                              param p,
                              const double_t delta,
                              const int reps_per_point)
    {
        road_1_lane_model::config base_cfg(config_path);
        const double_t x0 = field(base_cfg, p);
        const std::string tag = name_of(p);

        for (int k = -3; k <= 3; ++k)
        {
            auto cfg = base_cfg;
            field(cfg, p) = x0 + k * delta;

            const std::string prefix = out_dir + "/" + tag + "_x" + std::to_string(k);
            run_lab3_pack(cfg, prefix, reps_per_point, RUN_TIME);
        }

        std::ofstream meta(out_dir + "/meta.csv");
        meta << "variable,x0,delta,reps_per_point\n"
             << tag << ',' << x0 << ',' << delta << ',' << reps_per_point << '\n';
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
    run_lab3_shortened  (base_cfg, OUT_DIR + "lab3_shortened", 30);

    run_lab3_sensitivity(base_cfg, OUT_DIR + "lab3_sensitivity",
                         param::lambda_a, 0.01, 20);

    run_lab3_sensitivity(base_cfg, OUT_DIR + "lab3_sens_tgreen",
                         param::t_green, 4.0, 20);

    return 0;
}