#pragma once

#include <memory>

#include "i_runner.h"
#include "i_model.h"
#include "run_base.h"

class simple_runner : public runner::i_runner
{
public:
    simple_runner(std::shared_ptr<runner::i_model> model,
                  double_t run_time);

    void simulate() override;

private:
    std::shared_ptr<runner::i_model> model_;
    std::shared_ptr<runner::run_base> run_;
};
