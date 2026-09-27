#include "simple_runner.h"

simple_runner::simple_runner(std::shared_ptr<runner::i_model> model,
                             double_t run_time)
    : model_(std::move(model))
    , run_(std::make_shared<runner::run_base>(model_, run_time))
{
}

void simple_runner::simulate()
{
    run_->run();
}
