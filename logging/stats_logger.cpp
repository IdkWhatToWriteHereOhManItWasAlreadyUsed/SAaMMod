#include "stats_logger.h"

#include <cstdio>
#include <filesystem>
#include <stdexcept>
#include <string>

namespace logging
{
    namespace
    {
        std::string num(const double_t value)
        {
            char text[32];
            std::snprintf(text, sizeof(text), "%.10g", value);
            return text;
        }

        double_t mean_over_time(const double_t area, const double_t elapsed)
        {
            return (elapsed > 0) ? area / elapsed : 0;
        }

        void ensure_parent(const std::string& path)
        {
            const std::filesystem::path fp(path);
            if (fp.has_parent_path())
            {
                std::filesystem::create_directories(fp.parent_path());
            }
        }
    }

    stats_logger& stats_logger::instance()
    {
        static stats_logger singleton;
        return singleton;
    }

    stats_logger::~stats_logger()
    {
        summary_close();
        interval_close();
    }

    void stats_logger::summary_start(const std::string& path)
    {
        if (summary_file_.is_open()) { summary_file_.close(); }
        ensure_parent(path);
        summary_path_ = path;
        summary_file_.open(path, std::ios::out | std::ios::trunc);
        if (!summary_file_.is_open())
        {
            summary_path_.clear();
            throw std::runtime_error("cannot open summary: " + path);
        }
        summary_file_ << "replication,seed,Y,passed,wait_count,"
                         "max_queue_a,max_queue_b,run_time\n";
    }

    void stats_logger::write_replication(int rep, unsigned seed, double_t run_time)
    {
        if (!summary_file_.is_open()) { return; }
        summary_file_ << rep << ','
                      << seed << ','
                      << num(avg_wait()) << ','
                      << passed_ << ','
                      << wait_count_ << ','
                      << num(max_queue_a_) << ','
                      << num(max_queue_b_) << ','
                      << num(run_time) << '\n';
    }

    void stats_logger::summary_close()
    {
        if (summary_file_.is_open())
        {
            summary_file_.flush();
            summary_file_.close();
        }
        summary_path_.clear();
    }

    bool stats_logger::summary_active() const { return summary_file_.is_open(); }

    void stats_logger::interval_start(const std::string& path, double_t dt)
    {
        if (interval_file_.is_open()) { interval_file_.close(); }
        if (dt <= 0) { throw std::runtime_error("interval dt must be > 0"); }
        ensure_parent(path);
        interval_path_ = path;
        interval_dt_ = dt;
        interval_file_.open(path, std::ios::out | std::ios::trunc);
        if (!interval_file_.is_open())
        {
            interval_path_.clear();
            throw std::runtime_error("cannot open interval: " + path);
        }
        interval_file_ << "replication,model_time,Y_interval,"
                          "queue_a,queue_b,passed_interval\n";
    }

    void stats_logger::interval_close()
    {
        if (interval_file_.is_open())
        {
            interval_file_.flush();
            interval_file_.close();
        }
        interval_path_.clear();
    }

    bool stats_logger::interval_active() const { return interval_file_.is_open(); }

    void stats_logger::set_interval_rep(int rep) { interval_rep_ = rep; }

    void stats_logger::write_interval_row(double_t t)
    {
        const double_t y = (interval_wait_cnt_ > 0)
            ? interval_wait_sum_ / interval_wait_cnt_
            : 0.0;
        const int passed_interval = passed_ - interval_passed_at_;

        interval_file_ << interval_rep_ << ','
                       << num(t) << ','
                       << num(y) << ','
                       << num(cur_queue_a_) << ','
                       << num(cur_queue_b_) << ','
                       << passed_interval << '\n';

        interval_wait_sum_ = 0;
        interval_wait_cnt_ = 0;
        interval_passed_at_ = passed_;
    }

    void stats_logger::begin_run(double_t model_time)
    {
        run_start_ = model_time;
        last_time_ = model_time;
        cur_queue_a_ = 0;
        cur_queue_b_ = 0;
        area_a_ = 0;
        area_b_ = 0;
        max_queue_a_ = 0;
        max_queue_b_ = 0;
        passed_ = 0;
        wait_sum_ = 0;
        wait_count_ = 0;

        interval_next_ = model_time + interval_dt_;
        interval_wait_sum_ = 0;
        interval_wait_cnt_ = 0;
        interval_passed_at_ = 0;
    }

    void stats_logger::sample(const double_t model_time,
                              const std::size_t queue_a,
                              const std::size_t queue_b)
    {
        if (model_time > last_time_)
        {
            const double_t dt = model_time - last_time_;
            area_a_ += cur_queue_a_ * dt;
            area_b_ += cur_queue_b_ * dt;
        }
        last_time_ = model_time;
        cur_queue_a_ = static_cast<double_t>(queue_a);
        cur_queue_b_ = static_cast<double_t>(queue_b);
        if (cur_queue_a_ > max_queue_a_) { max_queue_a_ = cur_queue_a_; }
        if (cur_queue_b_ > max_queue_b_) { max_queue_b_ = cur_queue_b_; }

        if (!interval_file_.is_open()) { return; }
        while (model_time >= interval_next_)
        {
            write_interval_row(interval_next_);
            interval_next_ += interval_dt_;
        }
    }

    void stats_logger::car_passed(double_t /*passage_time*/)
    {
        ++passed_;
    }

    void stats_logger::car_waited(double_t wait_time)
    {
        wait_sum_ += wait_time;
        ++wait_count_;
        if (interval_file_.is_open())
        {
            interval_wait_sum_ += wait_time;
            ++interval_wait_cnt_;
        }
    }

    int stats_logger::wait_count() const { return wait_count_; }
    int stats_logger::passed() const { return passed_; }

    double_t stats_logger::avg_queue_a() const
    {
        return mean_over_time(area_a_, last_time_ - run_start_);
    }

    double_t stats_logger::avg_queue_b() const
    {
        return mean_over_time(area_b_, last_time_ - run_start_);
    }

    double_t stats_logger::max_queue_a() const { return max_queue_a_; }
    double_t stats_logger::max_queue_b() const { return max_queue_b_; }

    double_t stats_logger::avg_wait() const
    {
        return wait_count_ ? wait_sum_ / wait_count_ : 0;
    }
}