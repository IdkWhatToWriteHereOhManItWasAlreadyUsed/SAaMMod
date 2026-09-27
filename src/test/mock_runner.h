// mock_runner.h
#pragma once

#include "i_runner.h"
#include "run_base.h"
#include "mock_model.h"

namespace test
{
    class mock_runner : public runner::i_runner
    {
    public:
        explicit mock_runner(double run_time = 60.0,
                             int capacity = 2,
                             double interarrival_time = 3.0,
                             double service_time = 4.0)
            : model_(std::make_shared<mock_model>(capacity, interarrival_time, service_time, run_time))
            , run_(std::make_shared<runner::run_base>(model_, run_time))
        {}

        void simulate() override
        {
            run_->run();
        }
    private:
        std::shared_ptr<mock_model> model_;
        std::shared_ptr<runner::run_base> run_;
    };
}
