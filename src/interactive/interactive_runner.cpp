#include "interactive/interactive_runner.h"

interactive_runner::interactive_runner(
    std::shared_ptr<runner::i_model> model,
    const double_t run_time,
    std::shared_ptr<console_control> control)
    : model_(std::move(model))
    , run_(std::make_shared<runner::run_base>(model_, run_time))
    , control_(std::move(control))
{
}

void interactive_runner::simulate()
{
    control_->schedule(*run_);
    run_->run();
}

double_t interactive_runner::actual_run_time() const
{
    return run_->actual_run_time();
}
