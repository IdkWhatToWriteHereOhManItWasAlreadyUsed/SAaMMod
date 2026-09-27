#pragma once

#include <cstddef>
#include <string>
#include <unordered_map>
#include <vector>

namespace trace
{
    enum class car_action
    {
        arrive,
        enter,
        leave
    };

    struct car_event
    {
        double time = 0;
        int id = 0;
        char direction = 'A';
        car_action action = car_action::arrive;
    };

    struct light_event
    {
        double time = 0;
        char from = 'N';
        char to = 'N';
    };

    // Разобранный прогон. Формат строки лога:
    //   {"time":0.0,"sender":"traffic_light","data":{"from":"N","to":"A"}}
    //   {"time":7.9,"sender":"car","data":{"id":0,"action":"enter","direction":"A"}}
    struct data
    {
        std::vector<car_event> cars;                     // по возрастанию времени
        std::vector<light_event> lights;                 // по возрастанию времени
        std::unordered_map<int, double> car_leave_times; // id -> время отбытия
        double default_passage_time = 0;                 // медиана времени проезда
        double begin_time = 0;
        double end_time = 0;
    };

    // Бросает std::runtime_error с путём и номером строки при любой проблеме
    data load(const std::string& path);

    const char* action_name(car_action action);
}
