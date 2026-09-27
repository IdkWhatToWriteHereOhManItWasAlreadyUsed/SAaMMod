#include "trace.h"

#include <algorithm>
#include <fstream>
#include <memory>
#include <stdexcept>

#include <json/json.h>

namespace trace
{
    namespace
    {
        car_action parse_action(const std::string& text)
        {
            if (text == "arrive") return car_action::arrive;
            if (text == "enter") return car_action::enter;
            if (text == "leave") return car_action::leave;

            throw std::runtime_error("неизвестное действие машины: " + text);
        }

        char parse_direction(const Json::Value& value)
        {
            const std::string text = value.asString();
            return text.empty() ? 'N' : text.front();
        }
    }

    const char* action_name(const car_action action)
    {
        switch (action)
        {
            case car_action::arrive: return "arrive";
            case car_action::enter: return "enter";
            case car_action::leave: return "leave";
        }

        return "unknown";
    }

    data load(const std::string& path)
    {
        std::ifstream file(path);
        if (!file.is_open())
        {
            throw std::runtime_error("не удалось открыть лог: " + path);
        }

        Json::CharReaderBuilder reader_builder;
        std::unique_ptr<Json::CharReader> reader(reader_builder.newCharReader());

        data result;
        std::unordered_map<int, double> car_enter_times;
        bool has_records = false;

        std::string line;
        for (std::size_t line_no = 1; std::getline(file, line); ++line_no)
        {
            if (line.empty())
            {
                continue;
            }

            Json::Value record;
            std::string errors;
            if (!reader->parse(line.data(), line.data() + line.size(), &record, &errors))
            {
                throw std::runtime_error(path + ":" + std::to_string(line_no) + ": " + errors);
            }

            const double time = record["time"].asDouble();
            if (!has_records)
            {
                result.begin_time = time;
                has_records = true;
            }
            result.end_time = std::max(result.end_time, time);

            const Json::Value& payload = record["data"];
            if (record["sender"].asString() == "car")
            {
                car_event event;
                event.time = time;
                event.id = payload["id"].asInt();
                event.action = parse_action(payload["action"].asString());
                event.direction = parse_direction(payload["direction"]);
                result.cars.push_back(event);
            }
            else
            {
                light_event event;
                event.time = time;
                event.from = parse_direction(payload["from"]);
                event.to = parse_direction(payload["to"]);
                result.lights.push_back(event);
            }
        }

        if (!has_records)
        {
            throw std::runtime_error("лог не содержит ни одной записи: " + path);
        }

        // время отбытия каждой машины: при въезде оно уже известно, поэтому
        // прямоугольник можно двигать по линейному закону на всём поезде
        for (const car_event& event : result.cars)
        {
            if (event.action == car_action::enter)
            {
                car_enter_times[event.id] = event.time;
            }
            else if (event.action == car_action::leave)
            {
                result.car_leave_times[event.id] = event.time;
            }
        }

        // медиана времени проезда — запасной вариант для машин, чьё отбытие не
        // попало в лог, потому что прогон оборвался на горизонте
        std::vector<double> passages;
        passages.reserve(result.car_leave_times.size());
        for (const auto& [id, leave_time] : result.car_leave_times)
        {
            const auto enter = car_enter_times.find(id);
            if (enter != car_enter_times.end())
            {
                passages.push_back(leave_time - enter->second);
            }
        }
        if (!passages.empty())
        {
            const auto middle = passages.begin() + static_cast<std::ptrdiff_t>(passages.size() / 2);
            std::nth_element(passages.begin(), middle, passages.end());
            result.default_passage_time = *middle;
        }

        // stable_sort сохраняет порядок из лога для событий с одинаковым временем
        const auto by_time = [](const auto& lhs, const auto& rhs) { return lhs.time < rhs.time; };
        std::stable_sort(result.cars.begin(), result.cars.end(), by_time);
        std::stable_sort(result.lights.begin(), result.lights.end(), by_time);

        return result;
    }
}
