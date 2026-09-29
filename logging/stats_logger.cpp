#include "stats_logger.h"

#include <cstdio>
#include <filesystem>
#include <string>

namespace logging
{
    namespace
    {
        const char* const HEADER =
            "replication,modelTime,queue_a,avg_queue_a,queue_b,avg_queue_b,"
            "passed,max_queue_a,max_queue_b,passage,avg_passage,wait,avg_wait";

        // Короткая запись double без хвоста из нулей: анализатор сам приводит
        // значения к float, лишние разряды после 10 значащих цифр не нужны.
        std::string num(const double_t value)
        {
            char text[32];
            std::snprintf(text, sizeof(text), "%.10g", value);
            return text;
        }

        // Среднее по времени: площадь, делённая на время от начала прогона.
        double_t mean_over_time(const double_t area, const double_t elapsed)
        {
            return (elapsed > 0) ? area / elapsed : 0;
        }
    }

    stats_logger& stats_logger::instance()
    {
        static stats_logger singleton;
        return singleton;
    }

    stats_logger::~stats_logger()
    {
        close();
    }

    void stats_logger::start(const std::string& path, const int replication)
    {
        close();

        if (path.empty())
        {
            return;
        }

        const std::filesystem::path file_path(path);
        if (file_path.has_parent_path())
        {
            std::filesystem::create_directories(file_path.parent_path());
        }

        file_.open(path, std::ios::out | std::ios::trunc);
        if (!file_.is_open())
        {
            path_.clear();
            return;
        }

        path_ = path;
        buffer_.clear();
        replication_ = replication;
        begin_run(0);
        buffer_ += HEADER;
        buffer_ += "\n";
    }

    void stats_logger::close()
    {
        flush_buffer();

        if (file_.is_open())
        {
            file_.close();
        }
        path_.clear();
    }

    bool stats_logger::is_active() const
    {
        return file_.is_open();
    }

    const std::string& stats_logger::path() const
    {
        return path_;
    }

    void stats_logger::set_flush_size(const std::size_t bytes)
    {
        flush_size_ = bytes;
    }

    void stats_logger::set_replication(const int replication)
    {
        replication_ = replication;
    }

    int stats_logger::replication() const
    {
        return replication_;
    }

    void stats_logger::begin_run(const double_t model_time)
    {
        run_start_ = model_time;
        last_time_ = model_time;
        cur_queue_a_ = 0;
        cur_queue_b_ = 0;
        area_a_ = 0;
        area_b_ = 0;
        max_queue_a_ = 0;
        max_queue_b_ = 0;
        passage_ = 0;
        passage_sum_ = 0;
        passed_ = 0;
        wait_ = 0;
        wait_sum_ = 0;
        wait_count_ = 0;
    }

    void stats_logger::sample(const double_t model_time,
                              const std::size_t queue_a,
                              const std::size_t queue_b)
    {
        if (!file_.is_open())
        {
            return;
        }

        // очередь была постоянной на интервале (last_time_, model_time),
        // значит её вклад в среднее — длина, умноженная на длину интервала
        if (model_time > last_time_)
        {
            const double_t dt = model_time - last_time_;
            area_a_ += cur_queue_a_ * dt;
            area_b_ += cur_queue_b_ * dt;
        }
        last_time_ = model_time;

        cur_queue_a_ = queue_a;
        cur_queue_b_ = queue_b;

        if (queue_a > max_queue_a_) { max_queue_a_ = queue_a; }
        if (queue_b > max_queue_b_) { max_queue_b_ = queue_b; }

        write_row(model_time);

        if (buffer_.size() >= flush_size_)
        {
            flush_buffer();
        }
    }

    void stats_logger::car_passed(const double_t passage_time)
    {
        if (!file_.is_open())
        {
            return;
        }

        ++passed_;
        passage_ = passage_time;
        passage_sum_ += passage_time;
    }

    void stats_logger::car_waited(const double_t wait_time)
    {
        if (!file_.is_open())
        {
            return;
        }

        wait_ = wait_time;
        wait_sum_ += wait_time;
        ++wait_count_;
    }

    int stats_logger::passed() const
    {
        return passed_;
    }

    double_t stats_logger::avg_queue_a() const
    {
        return mean_over_time(area_a_, last_time_ - run_start_);
    }

    double_t stats_logger::avg_queue_b() const
    {
        return mean_over_time(area_b_, last_time_ - run_start_);
    }

    double_t stats_logger::max_queue_a() const
    {
        return max_queue_a_;
    }

    double_t stats_logger::max_queue_b() const
    {
        return max_queue_b_;
    }

    double_t stats_logger::passage() const
    {
        return passage_;
    }

    double_t stats_logger::avg_passage() const
    {
        return passed_ ? passage_sum_ / passed_ : 0;
    }

    double_t stats_logger::wait() const
    {
        return wait_;
    }

    double_t stats_logger::avg_wait() const
    {
        return wait_count_ ? wait_sum_ / wait_count_ : 0;
    }

    void stats_logger::write_row(const double_t model_time)
    {
        buffer_ += std::to_string(replication_);
        buffer_ += ",";
        buffer_ += num(model_time);
        buffer_ += ",";
        buffer_ += num(cur_queue_a_);
        buffer_ += ",";
        buffer_ += num(avg_queue_a());
        buffer_ += ",";
        buffer_ += num(cur_queue_b_);
        buffer_ += ",";
        buffer_ += num(avg_queue_b());
        buffer_ += ",";
        buffer_ += std::to_string(passed_);
        buffer_ += ",";
        buffer_ += num(max_queue_a_);
        buffer_ += ",";
        buffer_ += num(max_queue_b_);
        buffer_ += ",";
        buffer_ += num(passage_);
        buffer_ += ",";
        buffer_ += num(avg_passage());
        buffer_ += ",";
        buffer_ += num(wait_);
        buffer_ += ",";
        buffer_ += num(avg_wait());
        buffer_ += "\n";
    }

    void stats_logger::flush_buffer()
    {
        if (file_.is_open() && !buffer_.empty())
        {
            file_ << buffer_;
            file_.flush();
        }
        buffer_.clear();
    }
}
