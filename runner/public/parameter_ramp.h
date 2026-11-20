#pragma once

#include <cmath>
#include <fstream>
#include <memory>
#include <string>

#include "i_model.h"
#include "i_run.h"

namespace runner
{
    // Линейное изменение параметра модели по модельному времени:
    //   t = 0:            parameter = start
    //   t = interval:     parameter = start + step
    //   t = 2*interval:   parameter = start + 2*step
    //   ...
    // пока время не достигнет until. Работает через i_model::set_parameter,
    // поэтому подходит для любой модели, реализовавшей этот интерфейс.
    class parameter_ramp : public std::enable_shared_from_this<parameter_ramp>
    {
    public:
        parameter_ramp(i_model& model,
                       std::string parameter,
                       double_t start,
                       double_t step,
                       double_t interval,
                       double_t until,
                       std::string log_path = {});

        // Применить начальное значение и запланировать первое изменение.
        // Вызывается из i_model::reset.
        void start(i_run& run);

    private:
        bool set_value(i_run& run, double_t value);
        void schedule_next(i_run& run);
        void write_log(double_t time, double_t value, bool ok);

        i_model& model_;
        std::string parameter_;
        double_t value_;
        double_t step_;
        double_t interval_;
        double_t until_;
        std::string log_path_;
        std::ofstream log_file_;
    };
}
