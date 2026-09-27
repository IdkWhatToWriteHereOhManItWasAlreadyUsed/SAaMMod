// mock_model.h
#pragma once

#include <iostream>
#include <memory>
#include <string>

#include "i_model.h"
#include "i_run.h"
#include "mock_agent.h"
#include "mock_resource.h"

namespace test
{
    // Модель с очередью: агенты приходят с интервалом interarrival_time_,
    // обслуживаются за service_time_, ждут в очереди, если мест нет.
    class mock_model : public runner::i_model
    {
    public:
        mock_model(int capacity = 2,
                   double interarrival_time = 3.0,
                   double service_time = 4.0,
                   double run_time = 60.0)
            : resource_(std::make_shared<mock_resource>(capacity))
            , interarrival_time_(interarrival_time)
            , service_time_(service_time)
            , run_time_(run_time)
            , next_agent_id_(0)
        {}

        void reset(runner::i_run& run) override
        {
            log("reset", run.model_time(), "model initialized");
            schedule_arrival(run, interarrival_time_);
        }

        void stop(runner::i_run& run) override
        {
            log("stop", run.model_time(), "generator stopped");
        }

        void log(const std::string& action, double_t time, const std::string& msg)
        {
            std::cout << "[" << action << "] t=" << time << " " << msg << "\n";
        }

    private:
        // Генератор приходов: каждые interarrival_time_ минут приходит новый агент.
        void schedule_arrival(runner::i_run& run, double delay)
        {
            run.new_event
            (
                nullptr,
                [this, delay](runner::i_run& r)
                {
                    on_arrival(r);
                    if (r.model_time() + delay < run_time_)
                    {
                        schedule_arrival(r, delay);
                    }
                    r.delete_active_event();
                },
                run.model_time() + delay
            );
        }

        void on_arrival(runner::i_run& run)
        {
            auto agent = std::make_shared<mock_agent>(next_agent_id_++);
            log("arrive", run.model_time(), "agent #" + std::to_string(agent->id()));

            if (resource_->is_free())
            {
                start_service(run, agent);
            }
            else
            {
                resource_->push(agent);
                log("queue", run.model_time(),
                    "agent #" + std::to_string(agent->id()) +
                    " (queue=" + std::to_string(resource_->queue_size()) + ")");
            }
        }

        void start_service(runner::i_run& run, std::shared_ptr<mock_agent> agent)
        {
            resource_->use();
            log("start", run.model_time(), "agent #" + std::to_string(agent->id()));

            run.new_event
            (
                agent,
                [this, agent](runner::i_run& r)
                {
                    finish_service(r, agent);
                    r.delete_active_event();
                },
                run.model_time() + service_time_);
        }

        void finish_service(runner::i_run& run, std::shared_ptr<mock_agent> agent)
        {
            log("finish", run.model_time(), "agent #" + std::to_string(agent->id()));

            if (!resource_->queue_empty())
            {
                start_service(run, resource_->pop());
            }
            else
            {
                resource_->release();
            }
        }

        std::shared_ptr<mock_resource> resource_;
        double interarrival_time_;
        double service_time_;
        double run_time_;
        int next_agent_id_;
    };
}
