#pragma once

#include <cmath>
#include <cstddef>
#include <fstream>
#include <map>
#include <mutex>
#include <string>

namespace logging
{
    // Сборщик статистики ИМ. Накопители статистики одного прогона
    // thread-local, поэтому реплики можно выполнять параллельно: движок
    // не меняется, каждая реплика работает со своим ядром и по завершении
    // публикует снимок (publish). Файловые операции под мьютексом.
    class stats_logger
    {
    public:
        static stats_logger& instance();
        ~stats_logger();

        void summary_start(const std::string& path);
        // строка реплики пишется из опубликованного снимка
        void write_replication(int rep, unsigned seed, double_t run_time);
        void summary_close();
        bool summary_active() const;

        void interval_start(const std::string& path, double_t dt);
        void interval_close();
        // номер реплики для буфера интервалов ТЕКУЩЕГО потока
        void set_interval_rep(int rep);

        void begin_run(double_t model_time);
        void sample(double_t model_time, std::size_t queue_a, std::size_t queue_b);
        void car_passed(double_t passage_time);
        void car_waited(double_t wait_time);

        // опубликовать результаты прогона текущего потока как реплику rep:
        // снимок попадает в реестр для write_replication, буфер строк
        // интервалов дописывается в interval-файл
        void publish(int rep);

    private:
        stats_logger() = default;
        stats_logger(const stats_logger&) = delete;
        stats_logger& operator=(const stats_logger&) = delete;

        // потоково-локальное ядро накопления статистики одного прогона
        struct core;
        static core& get_core();

        struct snapshot
        {
            double_t y_sum = 0;
            int      y_cnt = 0;
            int      passed = 0;
            double_t max_a = 0;
            double_t max_b = 0;
        };
        snapshot take_snapshot();

        std::mutex io_;
        std::map<int, snapshot> snapshots_;

        std::ofstream summary_file_;
        std::string   summary_path_;

        // файловые члены; параметры интервала читаются рабочими потоками
        // из interval_dt_/interval_open_ до старта потоков (без гонок)
        std::ofstream interval_file_;
        std::string   interval_path_;
        double_t      interval_dt_ = 0;
        bool          interval_open_ = false;
    };
}
