#pragma once

#include "run_base.h"

namespace runner
{

    class drain_run : public run_base
    {
    public:
        using run_base::run_base;

    protected:
        bool end_of_run() override;

        void finish_run() override;
    };
}
