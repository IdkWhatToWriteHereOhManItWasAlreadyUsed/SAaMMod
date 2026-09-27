#pragma once
#include <cmath>
#include <string>

namespace runner
{
    class i_run;

    class i_model
    {
    public:
        virtual void reset(i_run& run) = 0;
        virtual void stop(i_run& run) = 0;
        virtual ~i_model() = default;
    };
}
