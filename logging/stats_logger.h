#pragma once

#include <cmath>
#include <cstddef>
#include <fstream>
#include <string>

namespace logging
{
    // Логгер статистики прогона. Пишет csv, по одному отсчёту на каждое
    // событие модели, плюс отсчёты в начале и в конце прогона:
    //   replication,modelTime,queue_a,avg_queue_a,queue_b,avg_queue_b,
    //   passed,max_queue_a,max_queue_b,passage,avg_passage,wait,avg_wait
    //
    // Смысл столбцов:
    //   queue_a, queue_b          — текущая длина очереди на момент отсчёта;
    //   avg_queue_a, avg_queue_b  — среднее по времени (площадь под длиной
    //                                очереди, делённая на время от начала прогона);
    //   passed                    — сколько машин уже проехало участок;
    //   max_queue_a, max_queue_b  — максимум длины очереди за прогон;
    //   passage                   — время прохождения последней уехавшей машины
    //                                (от прихода до выезда, вместе с ожиданием);
    //   avg_passage               — среднее арифметическое passage по уехавшим;
    //   wait                      — время ожидания в очереди последней въехавшей
    //                                машины (от прихода до начала движения);
    //   avg_wait                  — среднее арифметическое wait по въехавшим.
    //
    // Несколько прогонов пишутся в один файл: у каждого свой номер replication,
    // значения накапливаются заново с момента begin_run().
    class stats_logger
    {
    public:
        static stats_logger& instance();
        ~stats_logger();

        // Начать запись в path, записать строку заголовков и обнулить
        // накопленные величины. Незакрытый файл при этом закрывается.
        void start(const std::string& path, int replication = 1);

        // Дописать буфер и закрыть файл: после close() записи игнорируются.
        void close();

        bool is_active() const;

        // Путь текущего файла; пустая строка, если запись выключена.
        const std::string& path() const;

        // Порог размера буфера, при котором он сбрасывается в файл.
        void set_flush_size(std::size_t bytes);

        // Номер прогона для следующих строк (1, 2, 3, ...).
        void set_replication(int replication);
        int replication() const;

        // Начало прогона в момент model_time: обнуляет накопленные величины.
        void begin_run(double_t model_time);

        // Отсчёт в момент model_time с текущими длинами очередей.
        void sample(double_t model_time, std::size_t queue_a, std::size_t queue_b);

        // Машина проехала участок за passage_time (от прихода до выезда).
        void car_passed(double_t passage_time);

        // Машина начала движение (въехала на участок) после wait_time ожидания
        // в очереди (от прихода до начала движения).
        void car_waited(double_t wait_time);

        // Накопленные величины текущего прогона.
        int passed() const;
        double_t avg_queue_a() const;
        double_t avg_queue_b() const;
        double_t max_queue_a() const;
        double_t max_queue_b() const;
        double_t passage() const;
        double_t avg_passage() const;
        double_t wait() const;
        double_t avg_wait() const;

    private:
        stats_logger() = default;
        stats_logger(const stats_logger&) = delete;
        stats_logger& operator=(const stats_logger&) = delete;

        void flush_buffer();
        void write_row(double_t model_time);

        std::ofstream file_;
        std::string path_;
        std::string buffer_;
        std::size_t flush_size_ = 64 * 1024;
        int replication_ = 1;

        double_t run_start_ = 0;   // model_time начала прогона
        double_t last_time_ = 0;   // model_time последнего отсчёта
        double_t cur_queue_a_ = 0; // длина очереди на интервале после last_time_
        double_t cur_queue_b_ = 0;
        double_t area_a_ = 0;      // накопленная площадь под длиной очереди A
        double_t area_b_ = 0;
        double_t max_queue_a_ = 0;
        double_t max_queue_b_ = 0;
        double_t passage_ = 0;     // время прохождения последней уехавшей машины
        double_t passage_sum_ = 0;
        int passed_ = 0;
        double_t wait_ = 0;        // время ожидания последней въехавшей машины
        double_t wait_sum_ = 0;
        int wait_count_ = 0;
    };
}
