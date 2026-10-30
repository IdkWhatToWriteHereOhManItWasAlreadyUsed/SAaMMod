#pragma once

#include <memory>

#include "i_runner.h"
#include "i_model.h"
#include "drain_run.h"

class drain_runner : public runner::i_runner
{
public:
    drain_runner(std::shared_ptr<runner::i_model> model,
                 double_t run_time);

    void simulate() override;

private:
    std::shared_ptr<runner::i_model> model_;
    std::shared_ptr<runner::drain_run> run_;
};
