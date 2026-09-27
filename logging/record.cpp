#include "record.h"

namespace logging
{
    const Json::StreamWriterBuilder& record::writer()
    {
        // compact-запись: без отступов и комментариев
        static const Json::StreamWriterBuilder builder = []
        {
            Json::StreamWriterBuilder builder;
            builder["indentation"] = "";
            builder["commentStyle"] = "None";
            return builder;
        }();

        return builder;
    }

    void record::append_key(const std::string_view key)
    {
        if (data_.size() > 1) // не первый ключ — ставим запятую
        {
            data_ += ',';
        }
        data_ += value_of(key);
        data_ += ':';
    }

    record& record::add(const std::string_view key, const std::string_view value)
    {
        append_key(key);
        data_ += value_of(value);
        return *this;
    }

    record& record::add(const std::string_view key, const char value)
    {
        return add(key, std::string_view(&value, 1));
    }

    record& record::add(const std::string_view key, const double_t value)
    {
        append_key(key);
        data_ += value_of(value);
        return *this;
    }

    record& record::add(const std::string_view key, const int value)
    {
        append_key(key);
        data_ += value_of(value);
        return *this;
    }

    std::string record::str() const
    {
        return data_ + '}';
    }

    std::string record::value_of(const std::string_view value)
    {
        return Json::writeString(writer(), Json::Value(std::string(value)));
    }

    std::string record::value_of(const double_t value)
    {
        return Json::writeString(writer(), Json::Value(static_cast<double>(value)));
    }

    std::string record::value_of(const int value)
    {
        return Json::writeString(writer(), Json::Value(value));
    }
}
