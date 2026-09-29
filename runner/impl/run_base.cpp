#include "public/run_base.h"
#include <algorithm>

namespace runner
{
    run_base::run_base(std::shared_ptr<i_model> model, const double_t run_time)
        : run_time_(run_time), model_(model) {}

    void run_base::run()
    {
        model_time_ = 0;
        model_->reset(*this);
        is_halted_ = false;
        model_->sample(*this);

        while (!end_of_run())
        {
            model_time_ = next_time(events_[0].time);
            events_[0].handler(*this);
            model_->sample(*this);
        }
    }

    double_t run_base::model_time() const
    {
        return model_time_;
    }

    i_model& run_base::model()
    {
        return *model_;
    }

    void run_base::new_event(std::shared_ptr<i_agent> agent, handler_t handler, double time)
    {
        insert_event({agent, handler, time});
    }

    void run_base::move_active_event(double dif_time, handler_t handler)
    {
        events_[0].time += dif_time;
        if (handler)
        {
            events_[0].handler = handler;
        }
        event e = events_[0];
        events_.erase(events_.begin());
        insert_event(e);
    }

    void run_base::next_active_event(handler_t handler, std::shared_ptr<i_agent> agent)
    {
        if (handler)
        {
            events_[0].handler = handler;
        }
        if (agent)
        {
            events_[0].agent = agent;
        }
    }

    void run_base::delete_active_event()
    {
        events_.erase(events_.begin());
    }

    void run_base::delete_event(std::shared_ptr<i_agent> agent)
    {
        auto it = std::find_if(
            events_.begin(),
            events_.end(),
            [&](const event& e) { return e.agent == agent; }
        );

        if (it != events_.end())
        {
            events_.erase(it);
        }
    }

    bool run_base::end_of_run()
    {
        if (!is_empty() && is_active()) return false;
        if (!is_halted_) { model_->stop(*this); is_halted_ = true; }
        if (!is_empty()) return false;
        return true;
    }

    bool run_base::is_active()
    {
        return model_time_ < run_time_;
    }

    bool run_base::is_empty()
    {
        return true;
    }

    double_t run_base::next_time(const double_t base_time)
    {
        return base_time;
    }

    void run_base::insert_event(const event& e)
    {
        events_.insert(std::upper_bound(events_.begin(), events_.end(), e), e);
    }
}