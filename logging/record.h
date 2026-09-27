#pragma once

#include <cmath>
#include <string>
#include <string_view>

#include <json/json.h>

namespace logging
{
    // Поля одной записи журнала в заданном порядке. Нужен потому, что jsoncpp
    // хранит ключи объекта в std::map и печатает их по алфавиту, а в логе
    // порядок полей задан. Сами значения по-прежнему сериализует jsoncpp,
    // вместе с экранированием.
    class record
    {
    public:
        record& add(std::string_view key, std::string_view value);
        record& add(std::string_view key, char value);
        record& add(std::string_view key, double_t value);
        record& add(std::string_view key, int value);

        // Готовая json-строка объекта: {"key":value,...}
        std::string str() const;

        // Одиночное значение, сериализованное jsoncpp.
        static std::string value_of(std::string_view value);
        static std::string value_of(double_t value);
        static std::string value_of(int value);

    private:
        static const Json::StreamWriterBuilder& writer();

        void append_key(std::string_view key);

        std::string data_ = "{";
    };
}
