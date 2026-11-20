#pragma once

#include <memory>

#include "console_control.h"
#include "i_model.h"
#include "i_runner.h"
#include "run_base.h"

// Раннер для интерактивного сценария: перед запуском планирует опросы
// console_control, дальше работает обычный run_base.
class interactive_runner : public runner::i_runner
{
public:
    interactive_runner(std::shared_ptr<runner::i_model> model,
                       double_t run_time,
                       std::shared_ptr<console_control> control);

    void simulate() override;

    // Фактическая длительность прогона (может быть меньше run_time,
    // если пользователь завершил прогон командой q).
    double_t actual_run_time() const;

private:
    std::shared_ptr<runner::i_model> model_;
    std::shared_ptr<runner::run_base> run_;
    std::shared_ptr<console_control> control_;
};
