// mock_model.h
#pragma once
#include "i_model.h"
#include "i_run.h"
#include <iostream>

namespace test
{
    class mock_model : public runner::i_model
    {
    public:
        void reset(runner::i_run& run) override
        {
            std::cout << "reset at t=" << run.model_time() << "\n";
            run.new_event
            (
                nullptr,
                [](runner::i_run& r)
                {
                    std::cout << "event at t=" << r.model_time() << "\n";
                    r.new_event
                    (
                        nullptr,
                        [](runner::i_run& r2)
                        {
                            std::cout << "event at t=" << r2.model_time() << "\n";
                            r2.delete_active_event();
                        },
                        r.model_time() + 5.0);
                    r.delete_active_event();
                },
                5.0);
        }

        void stop(runner::i_run& run) override
        {
            std::cout << "stop at t=" << run.model_time() << "\n";
        }

        void log(const std::string& action, double_t time, const std::string& msg) override
        {
            std::cout << action << " " << time << " " << msg << "\n";
        }
    };
}