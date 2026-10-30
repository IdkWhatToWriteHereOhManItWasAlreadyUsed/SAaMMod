#include "drain_runner.h"

drain_runner::drain_runner(std::shared_ptr<runner::i_model> model,
                           double_t run_time)
    : model_(std::move(model))
    , run_(std::make_shared<runner::drain_run>(model_, run_time))
{
}

void drain_runner::simulate()
{
    run_->run();
}
