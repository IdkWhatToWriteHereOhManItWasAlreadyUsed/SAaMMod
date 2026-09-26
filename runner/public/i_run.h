#pragma once
#include <cmath>
#include <memory>

#include "event.h"

namespace runner
{
    class i_agent;
    class i_model;

    class i_run
    {
    public:
        virtual ~i_run() = default;
        virtual void run() = 0;

        virtual double_t model_time() const = 0;
        virtual i_model& model() = 0;
        virtual void new_event(std::shared_ptr<i_agent> agent, handler_t handler, double time) = 0;
        virtual void move_active_event(double dif_time, handler_t handler) = 0;
        virtual void next_active_event(handler_t handler, std::shared_ptr<i_agent> agent) = 0;
        virtual void delete_active_event() = 0;
        virtual void delete_event(std::shared_ptr<i_agent> agent) = 0;
    };
}
