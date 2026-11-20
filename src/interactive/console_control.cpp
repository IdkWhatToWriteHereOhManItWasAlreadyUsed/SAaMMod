#include "interactive/console_control.h"

#include <cstdlib>
#include <filesystem>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <utility>

#include "stats_logger.h"

namespace
{
    std::string shell_quote(const std::string& text)
    {
        std::string quoted = "'";
        for (const char ch : text)
        {
            if (ch == '\'')
            {
                quoted += "'\\''";
            }
            else
            {
                quoted += ch;
            }
        }
        quoted += '\'';
        return quoted;
    }

    std::string trim(const std::string& text)
    {
        const std::string whitespace = " \t\r\n";
        const std::size_t begin = text.find_first_not_of(whitespace);
        if (begin == std::string::npos)
        {
            return {};
        }
        const std::size_t end = text.find_last_not_of(whitespace);
        return text.substr(begin, end - begin + 1);
    }
}

console_control::console_control(runner::i_model& model,
                                 std::string parameter,
                                 const double_t start_value,
                                 const double_t default_delta,
                                 const double_t interval,
                                 const double_t until,
                                 std::string csv_path,
                                 std::string script_path,
                                 std::string log_path)
    : model_(model)
    , parameter_(std::move(parameter))
    , value_(start_value)
    , delta_(default_delta)
    , interval_(interval)
    , until_(until)
    , csv_path_(std::move(csv_path))
    , script_path_(std::move(script_path))
    , log_path_(std::move(log_path))
{
    if (!(interval_ > 0.0) || !std::isfinite(interval_))
    {
        throw std::invalid_argument("console_control: interval must be > 0");
    }
}

void console_control::open_log()
{
    const std::filesystem::path path(log_path_);
    if (path.has_parent_path())
    {
        std::filesystem::create_directories(path.parent_path());
    }
    log_file_.open(log_path_, std::ios::out | std::ios::trunc);
    if (log_file_.is_open())
    {
        log_file_ << "model_time,parameter,value,source\n";
    }
}

void console_control::schedule(runner::i_run& run)
{
    open_log();

    if (!model_.set_parameter(parameter_, value_))
    {
        std::cerr << "console_control: модель отклонила начальное значение "
                  << parameter_ << "=" << value_ << '\n';
    }
    write_log(run.model_time(), value_, "start");

    const double_t next_time = run.model_time() + interval_;
    if (next_time >= until_)
    {
        return;
    }

    auto self = shared_from_this();
    run.new_event
    (
        nullptr,
        [self](runner::i_run& r) { self->tick(r); },
        next_time
    );
}

void console_control::tick(runner::i_run& run)
{
    // Данные до текущего момента должны быть на диске: Python читает csv.
    logging::stats_logger::instance().flush_intervals();

    const plot_choice choice = ask_plot_choice(run);
    if (choice == plot_choice::halt)
    {
        run.delete_active_event();
        return;
    }
    if (choice == plot_choice::show)
    {
        show_plot(run);
    }

    if (!ask_and_apply(run))
    {
        run.delete_active_event();
        return;
    }

    const double_t next_time = run.model_time() + interval_;
    if (next_time < until_)
    {
        auto self = shared_from_this();
        run.new_event
        (
            nullptr,
            [self](runner::i_run& r) { self->tick(r); },
            next_time
        );
    }

    run.delete_active_event();
}

console_control::plot_choice console_control::ask_plot_choice(
    runner::i_run& run)
{
    std::cout << "\nt=" << run.model_time()
              << ", " << parameter_ << "=" << value_
              << ". Показать график? [Enter/любой символ = нет, y = да]: "
              << std::flush;

    std::string line;
    if (!std::getline(std::cin, line))
    {
        std::cout << "\nввод закрыт — завершаю прогон\n";
        run.halt();
        return plot_choice::halt;
    }

    line = trim(line);
    if (line == "y" || line == "Y")
    {
        return plot_choice::show;
    }
    return plot_choice::skip;
}

void console_control::show_plot(runner::i_run& run) const
{
    std::ostringstream command;
    command << "python3 "
            << shell_quote(script_path_)
            << " --csv " << shell_quote(csv_path_)
            << " --param " << shell_quote(parameter_)
            << " --value " << value_
            << " --time " << run.model_time()
            << " --log " << shell_quote(log_path_);

    const int status = std::system(command.str().c_str());
    if (status != 0)
    {
        std::cerr << "console_control: не удалось показать график "
                     "(код " << status << ")\n";
    }
}

bool console_control::ask_and_apply(runner::i_run& run)
{
    while (true)
    {
        std::cout << "\nt=" << run.model_time()
                  << ", " << parameter_ << "=" << value_
                  << ". Новое значение [Enter = " << value_ + delta_
                  << ", q = завершить]: " << std::flush;

        std::string line;
        if (!std::getline(std::cin, line))
        {
            std::cout << "\nввод закрыт — завершаю прогон\n";
            run.halt();
            return false;
        }

        line = trim(line);
        if (line == "q" || line == "Q" ||
            line == "quit" || line == "stop")
        {
            run.halt();
            return false;
        }

        double_t candidate = value_ + delta_;
        bool automatic = true;
        if (!line.empty())
        {
            try
            {
                std::size_t parsed = 0;
                candidate = std::stod(line, &parsed);
                if (parsed != line.size())
                {
                    throw std::invalid_argument("trailing characters");
                }
                automatic = false;
            }
            catch (const std::exception&)
            {
                std::cout << "не удалось разобрать число: " << line << '\n';
                continue;
            }
        }

        if (!std::isfinite(candidate) || candidate <= 0.0)
        {
            std::cout << "значение должно быть положительным\n";
            continue;
        }

        if (!model_.set_parameter(parameter_, candidate))
        {
            std::cout << "модель отклонила значение " << candidate << '\n';
            continue;
        }

        const double_t previous = value_;
        value_ = candidate;
        write_log(run.model_time(), value_, automatic ? "auto" : "manual");
        std::cout << parameter_ << ": " << previous << " -> " << value_ << '\n';
        return true;
    }
}

void console_control::write_log(const double_t time,
                                const double_t value,
                                const char* source)
{
    if (!log_file_.is_open())
    {
        return;
    }
    log_file_ << time << ',' << parameter_ << ',' << value << ','
              << source << '\n';
    log_file_.flush();
}
