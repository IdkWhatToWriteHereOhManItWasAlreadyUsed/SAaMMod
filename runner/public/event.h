#pragma once
#include <cmath>
#include <functional>
#include <memory>
#include "i_agent.h"

namespace runner
{
    class i_run;

    using handler_t = std::function<void(i_run&)>;

    class event
    {
    public:
        std::shared_ptr<i_agent> agent;
        handler_t handler;
        double_t time;

        bool operator>(const event& other) const
        {
            return time > other.time;
        }

        bool operator<(const event& other) const
        {
            return time < other.time;
        }
    };
}
