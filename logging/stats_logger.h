#pragma once

#include <cmath>
#include <cstddef>
#include <fstream>
#include <string>

namespace logging
{
    class stats_logger
    {
    public:
        static stats_logger& instance();
        ~stats_logger();

        void summary_start(const std::string& path);
        void write_replication(int rep, unsigned seed, double_t run_time);
        void summary_close();
        bool summary_active() const;

        void interval_start(const std::string& path, double_t dt);
        void interval_close();
        bool interval_active() const;
        void set_interval_rep(int rep);

        void begin_run(double_t model_time);
        void sample(double_t model_time, std::size_t queue_a, std::size_t queue_b);
        void car_passed(double_t passage_time);
        void car_waited(double_t wait_time);

        int wait_count() const;
        int passed() const;
        double_t avg_queue_a() const;
        double_t avg_queue_b() const;
        double_t max_queue_a() const;
        double_t max_queue_b() const;
        double_t avg_wait() const;

    private:
        stats_logger() = default;
        stats_logger(const stats_logger&) = delete;
        stats_logger& operator=(const stats_logger&) = delete;

        void write_interval_row(double_t t);

        double_t run_start_ = 0;
        double_t last_time_ = 0;
        double_t cur_queue_a_ = 0;
        double_t cur_queue_b_ = 0;
        double_t area_a_ = 0;
        double_t area_b_ = 0;
        double_t max_queue_a_ = 0;
        double_t max_queue_b_ = 0;
        int passed_ = 0;
        double_t wait_sum_ = 0;
        int wait_count_ = 0;

        std::ofstream summary_file_;
        std::string   summary_path_;

        std::ofstream interval_file_;
        std::string   interval_path_;
        double_t      interval_dt_ = 0;
        double_t      interval_next_ = 0;
        double_t      interval_wait_sum_ = 0;
        int           interval_wait_cnt_ = 0;
        int           interval_passed_at_ = 0;
        int           interval_rep_ = 1;
    };
}