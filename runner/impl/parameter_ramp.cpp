#include "public/parameter_ramp.h"

#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <utility>

namespace runner
{
    parameter_ramp::parameter_ramp(i_model& model,
                                   std::string parameter,
                                   const double_t start,
                                   const double_t step,
                                   const double_t interval,
                                   const double_t until,
                                   std::string log_path)
        : model_(model)
        , parameter_(std::move(parameter))
        , value_(start)
        , step_(step)
        , interval_(interval)
        , until_(until)
        , log_path_(std::move(log_path))
    {
        if (!(interval_ > 0.0) || !std::isfinite(interval_))
        {
            throw std::invalid_argument("parameter_ramp: interval must be > 0");
        }
    }

    void parameter_ramp::start(i_run& run)
    {
        if (!log_path_.empty())
        {
            const std::filesystem::path path(log_path_);
            if (path.has_parent_path())
            {
                std::filesystem::create_directories(path.parent_path());
            }
            log_file_.open(log_path_, std::ios::out | std::ios::trunc);
            if (log_file_.is_open())
            {
                log_file_ << "model_time,parameter,value,ok\n";
            }
        }

        // Начальное значение применяется сразу, до первого события модели.
        if (set_value(run, value_))
        {
            schedule_next(run);
        }
    }

    void parameter_ramp::schedule_next(i_run& run)
    {
        const double_t next_time = run.model_time() + interval_;
        if (next_time >= until_)
        {
            return;
        }

        auto self = shared_from_this();
        run.new_event
        (
            nullptr,
            [self](i_run& r)
            {
                if (self->set_value(r, self->value_ + self->step_))
                {
                    self->schedule_next(r);
                }
                r.delete_active_event();
            },
            next_time
        );
    }

    bool parameter_ramp::set_value(i_run& run, const double_t value)
    {
        const bool ok = model_.set_parameter(parameter_, value);
        if (ok)
        {
            value_ = value;
        }
        write_log(run.model_time(), value, ok);

        std::cout << "[ramp] t=" << run.model_time()
                  << " " << parameter_ << "=" << value
                  << (ok ? "" : " (не изменён)") << '\n';
        return ok;
    }

    void parameter_ramp::write_log(const double_t time,
                                   const double_t value,
                                   const bool ok)
    {
        if (!log_file_.is_open())
        {
            return;
        }
        log_file_ << time << ',' << parameter_ << ',' << value << ','
                  << (ok ? 1 : 0) << '\n';
    }
}
