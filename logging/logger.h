#pragma once

#include <cmath>
#include <cstddef>
#include <fstream>
#include <string>
#include <string_view>

#include "record.h"

namespace logging
{
    // Глобальный журнал событий модели. Каждая запись — отдельная строка json:
    //   {"timestamp":0.0,"sender":"traffic_light","from":"N","to":"A"}
    //   {"timestamp":7.94,"sender":"car","id":0,"action":"arrive","direction":"A"}
    class logger
    {
    public:
        static logger& instance();
        ~logger();

        // Начать запись в path. Незакрытый файл при этом закрывается, поэтому
        // смену пути во время работы программы делают просто повторным start().
        void start(const std::string& path);

        // Дописать буфер, закрыть файл и сбросить путь в пустую строку:
        // после close() записи молча игнорируются до следующего start().
        void close();

        bool is_active() const;

        // Путь текущего файла; пустая строка, если запись выключена.
        const std::string& path() const;

        // Порог размера буфера, при котором он сбрасывается в файл.
        void set_flush_size(std::size_t bytes);

        void write(double_t model_time, std::string_view sender, const record& fields);
        void write_car(double_t model_time, int id, std::string_view action, char direction);
        void write_light(double_t model_time, char from, char to);

    private:
        logger() = default;
        logger(const logger&) = delete;
        logger& operator=(const logger&) = delete;

        void flush_buffer();

        std::ofstream file_;
        std::string path_;
        std::string buffer_;
        std::size_t flush_size_ = 64 * 1024;
    };
}
