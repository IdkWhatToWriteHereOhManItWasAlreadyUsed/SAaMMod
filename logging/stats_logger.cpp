#include "stats_logger.h"

#include <cstdio>
#include <filesystem>
#include <stdexcept>
#include <string>
#include <vector>

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

        void ensure_parent(const std::string& path)
        {
            const std::filesystem::path fp(path);
            if (fp.has_parent_path())
            {
                std::filesystem::create_directories(fp.parent_path());
            }
        }
    }

    // ---- потоково-локальное ядро: вся накопительная статистика прогона ----

    struct stats_logger::core
    {
        double_t run_start_ = 0;
        double_t last_time_ = 0;
        double_t cur_a_ = 0;
        double_t cur_b_ = 0;
        double_t area_a_ = 0;
        double_t area_b_ = 0;
        double_t max_a_ = 0;
        double_t max_b_ = 0;
        int      passed_ = 0;
        double_t wait_sum_ = 0;
        int      wait_cnt_ = 0;

        double_t interval_dt_ = 0;
        double_t interval_next_ = 0;
        double_t interval_wait_sum_ = 0;
        int      interval_wait_cnt_ = 0;
        int      interval_passed_at_ = 0;
        int      interval_rep_ = 1;
        std::vector<std::string> interval_rows_;   // буфер строк текущей реплики
    };

    stats_logger::core& stats_logger::get_core()
    {
        static thread_local core c;
        return c;
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

    // ---- summary ----

    void stats_logger::summary_start(const std::string& path)
    {
        std::lock_guard lock(io_);
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
        std::lock_guard lock(io_);
        if (!summary_file_.is_open()) { return; }

        const auto it = snapshots_.find(rep);
        if (it == snapshots_.end()) { return; }
        const snapshot& s = it->second;
        const double_t y = (s.y_cnt > 0) ? s.y_sum / s.y_cnt : 0.0;

        summary_file_ << rep << ','
                      << seed << ','
                      << num(y) << ','
                      << s.passed << ','
                      << s.y_cnt << ','
                      << num(s.max_a) << ','
                      << num(s.max_b) << ','
                      << num(run_time) << '\n';
        snapshots_.erase(it);
    }

    void stats_logger::summary_close()
    {
        std::lock_guard lock(io_);
        if (summary_file_.is_open())
        {
            summary_file_.flush();
            summary_file_.close();
        }
        summary_path_.clear();
    }

    bool stats_logger::summary_active() const { return summary_file_.is_open(); }

    // ---- interval ----

    void stats_logger::interval_start(const std::string& path, double_t dt)
    {
        std::lock_guard lock(io_);
        if (interval_file_.is_open()) { interval_file_.close(); }
        if (dt <= 0) { throw std::runtime_error("interval dt must be > 0"); }
        ensure_parent(path);
        interval_path_ = path;
        interval_dt_ = dt;
        interval_file_.open(path, std::ios::out | std::ios::trunc);
        if (!interval_file_.is_open())
        {
            interval_path_.clear();
            interval_dt_ = 0;
            throw std::runtime_error("cannot open interval: " + path);
        }
        interval_file_ << "replication,model_time,Y_interval,Y_cum,"
                          "queue_a,queue_b,passed_interval,w_count_interval\n";
        interval_open_ = true;
    }

    void stats_logger::interval_close()
    {
        std::lock_guard lock(io_);
        if (interval_file_.is_open())
        {
            interval_file_.flush();
            interval_file_.close();
        }
        interval_path_.clear();
        interval_dt_ = 0;
        interval_open_ = false;
    }

    void stats_logger::set_interval_rep(int rep)
    {
        get_core().interval_rep_ = rep;
    }

    // ---- накопление (каждый поток — своё ядро) ----

    void stats_logger::begin_run(double_t model_time)
    {
        core& c = get_core();

        c.run_start_ = model_time;
        c.last_time_ = model_time;
        c.cur_a_ = 0;
        c.cur_b_ = 0;
        c.area_a_ = 0;
        c.area_b_ = 0;
        c.max_a_ = 0;
        c.max_b_ = 0;
        c.passed_ = 0;
        c.wait_sum_ = 0;
        c.wait_cnt_ = 0;

        // параметры интервала заданы interval_start ДО запуска потоков
        c.interval_dt_ = interval_open_ ? interval_dt_ : 0.0;
        c.interval_next_ = model_time + c.interval_dt_;
        c.interval_wait_sum_ = 0;
        c.interval_wait_cnt_ = 0;
        c.interval_passed_at_ = 0;
        c.interval_rows_.clear();
    }

    void stats_logger::sample(const double_t model_time,
                              const std::size_t queue_a,
                              const std::size_t queue_b)
    {
        core& c = get_core();

        if (model_time > c.last_time_)
        {
            const double_t dt = model_time - c.last_time_;
            c.area_a_ += c.cur_a_ * dt;
            c.area_b_ += c.cur_b_ * dt;
        }
        c.last_time_ = model_time;
        c.cur_a_ = static_cast<double_t>(queue_a);
        c.cur_b_ = static_cast<double_t>(queue_b);
        if (c.cur_a_ > c.max_a_) { c.max_a_ = c.cur_a_; }
        if (c.cur_b_ > c.max_b_) { c.max_b_ = c.cur_b_; }

        if (c.interval_dt_ <= 0) { return; }
        while (model_time >= c.interval_next_)
        {
            const double_t t = c.interval_next_;
            // честное среднее за интервал: только машины, начавшие
            // движение в нём; кумулятив пишется отдельно (визуализация)
            const double_t y_cum = (c.wait_cnt_ > 0)
                ? c.wait_sum_ / c.wait_cnt_ : 0.0;
            const double_t y_int = (c.interval_wait_cnt_ > 0)
                ? c.interval_wait_sum_ / c.interval_wait_cnt_ : 0.0;
            const int passed_interval = c.passed_ - c.interval_passed_at_;

            c.interval_rows_.push_back(
                std::to_string(c.interval_rep_) + ',' + num(t) + ','
                + (c.interval_wait_cnt_ > 0 ? num(y_int) : std::string("NA"))
                + ',' + num(y_cum) + ','
                + num(c.cur_a_) + ',' + num(c.cur_b_) + ','
                + std::to_string(passed_interval) + ','
                + std::to_string(c.interval_wait_cnt_) + '\n');

            c.interval_wait_sum_ = 0;
            c.interval_wait_cnt_ = 0;
            c.interval_passed_at_ = c.passed_;
            c.interval_next_ += c.interval_dt_;
        }
    }

    void stats_logger::car_passed(double_t /*passage_time*/)
    {
        ++get_core().passed_;
    }

    void stats_logger::car_waited(double_t wait_time)
    {
        core& c = get_core();
        c.wait_sum_ += wait_time;
        ++c.wait_cnt_;
        if (c.interval_dt_ > 0)
        {
            c.interval_wait_sum_ += wait_time;
            ++c.interval_wait_cnt_;
        }
    }

    // ---- публикация результатов прогона ----

    stats_logger::snapshot stats_logger::take_snapshot()
    {
        const core& c = get_core();
        return snapshot{ c.wait_sum_, c.wait_cnt_, c.passed_,
                         c.max_a_, c.max_b_ };
    }

    void stats_logger::publish(int rep)
    {
        core& c = get_core();

        std::lock_guard lock(io_);
        if (!c.interval_rows_.empty() && interval_file_.is_open())
        {
            for (const std::string& row : c.interval_rows_)
            {
                interval_file_ << row;
            }
            interval_file_.flush();
        }
        c.interval_rows_.clear();

        snapshots_[rep] = take_snapshot();
    }
}
