#pragma once

#include <cmath>
#include <fstream>
#include <memory>
#include <string>

#include "i_model.h"
#include "i_run.h"

// Интерактивное управление параметром во время прогона.
//
// Раз в interval модельных секунд:
//   1) сбрасывает накопленную статистику в csv;
//   2) вызывает Python-скрипт, который показывает график до текущего момента;
//   3) спрашивает новое значение параметра в консоли
//      (Enter — текущее + delta, q — досрочно завершить прогон);
//   4) применяет значение через i_model::set_parameter.
class console_control : public std::enable_shared_from_this<console_control>
{
public:
    console_control(runner::i_model& model,
                    std::string parameter,
                    double_t start_value,
                    double_t default_delta,
                    double_t interval,
                    double_t until,
                    std::string csv_path,
                    std::string script_path,
                    std::string log_path);

    // Записать начальное значение и запланировать первый опрос.
    void schedule(runner::i_run& run);

private:
    enum class plot_choice { show, skip, halt };

    void tick(runner::i_run& run);
    plot_choice ask_plot_choice(runner::i_run& run);
    void show_plot(runner::i_run& run) const;
    bool ask_and_apply(runner::i_run& run);
    void write_log(double_t time, double_t value, const char* source);
    void open_log();

    runner::i_model& model_;
    std::string parameter_;
    double_t value_;
    double_t delta_;
    double_t interval_;
    double_t until_;

    std::string csv_path_;
    std::string script_path_;
    std::string log_path_;
    std::ofstream log_file_;
};
