#include "logger.h"

#include <filesystem>

namespace logging
{
    logger& logger::instance()
    {
        static logger singleton;
        return singleton;
    }

    logger::~logger()
    {
        close();
    }

    void logger::start(const std::string& path)
    {
        close();

        if (path.empty())
        {
            return;
        }

        const std::filesystem::path file_path(path);
        if (file_path.has_parent_path())
        {
            std::filesystem::create_directories(file_path.parent_path());
        }

        file_.open(path, std::ios::out | std::ios::trunc);
        if (!file_.is_open())
        {
            path_.clear();
            return;
        }

        path_ = path;
        buffer_.clear();
    }

    void logger::close()
    {
        flush_buffer();

        if (file_.is_open())
        {
            file_.close();
        }
        path_.clear();
    }

    bool logger::is_active() const
    {
        return file_.is_open();
    }

    const std::string& logger::path() const
    {
        return path_;
    }

    void logger::set_flush_size(const std::size_t bytes)
    {
        flush_size_ = bytes;
    }

    void logger::write(const double_t model_time,
                       const std::string_view sender,
                       const record& fields)
    {
        if (!file_.is_open())
        {
            return;
        }

        buffer_ += "{\"timestamp\":" + record::value_of(model_time);
        buffer_ += ",\"sender\":" + record::value_of(sender);

        const std::string body = fields.str();
        if (body.size() > 2) // набор полей непустой
        {
            buffer_ += ',' + body;
        }
        buffer_ += "}\n";

        if (buffer_.size() >= flush_size_)
        {
            flush_buffer();
        }
    }

    void logger::write_car(const double_t model_time,
                           const int id,
                           const std::string_view action,
                           const char direction)
    {
        write(model_time, "car",
              record()
                  .add("id", id)
                  .add("action", action)
                  .add("direction", direction));
    }

    void logger::write_light(const double_t model_time, const char from, const char to)
    {
        write(model_time, "traffic_light",
              record()
                  .add("from", from)
                  .add("to", to));
    }

    void logger::flush_buffer()
    {
        if (file_.is_open() && !buffer_.empty())
        {
            file_ << buffer_;
            file_.flush();
        }
        buffer_.clear();
    }
}
