#include "scene.h"

#include <algorithm>

namespace scene
{
    namespace
    {
        // Позиция в очереди именно этого направления: у A и B очереди
        // независимые, а храним мы их одним списком в порядке прибытия
        std::size_t queue_position(const std::vector<waiting_car>& queue,
                                   const char direction,
                                   const int id)
        {
            std::size_t position = 0;
            for (std::size_t i = 0; i < queue.size(); ++i)
            {
                if (queue[i].direction != direction)
                {
                    continue;
                }
                if (queue[i].id == id)
                {
                    return position;
                }
                ++position;
            }

            return queue.size();
        }
    }

    scene::scene(const trace::data& data)
        : data_(data)
    {
        reset();
    }

    void scene::reset()
    {
        car_cursor_ = 0;
        light_cursor_ = 0;
        time_ = data_.begin_time;
        phase_ = 'N';
        waiting_.clear();
        moving_.clear();
    }

    void scene::advance_to(const double model_time)
    {
        if (model_time < time_)
        {
            reset();
        }

        while (true)
        {
            // события за пределами model_time пока не трогаем
            const trace::car_event* car = next_car();
            if (car && car->time > model_time)
            {
                car = nullptr;
            }

            const trace::light_event* light = next_light();
            if (light && light->time > model_time)
            {
                light = nullptr;
            }

            // при равном времени сначала машины: въезд на зелёный должен
            // накладываться на переключение, а не наоборот
            if (car && (!light || car->time <= light->time))
            {
                ++car_cursor_;
                apply(*car);
                continue;
            }

            if (light)
            {
                ++light_cursor_;
                apply(*light);
                continue;
            }

            break;
        }

        time_ = model_time;
    }

    double scene::begin_time() const { return data_.begin_time; }
    double scene::end_time() const { return data_.end_time; }
    double scene::time() const { return time_; }
    char scene::light_phase() const { return phase_; }
    double scene::passage_time() const { return data_.default_passage_time; }
    const std::vector<waiting_car>& scene::waiting() const { return waiting_; }
    const std::vector<moving_car>& scene::moving() const { return moving_; }

    const trace::car_event* scene::next_car() const
    {
        return car_cursor_ < data_.cars.size() ? &data_.cars[car_cursor_] : nullptr;
    }

    const trace::light_event* scene::next_light() const
    {
        return light_cursor_ < data_.lights.size() ? &data_.lights[light_cursor_] : nullptr;
    }

    void scene::apply(const trace::car_event& event)
    {
        switch (event.action)
        {
            case trace::car_action::arrive:
                waiting_.push_back({event.id, event.direction});
                break;

            case trace::car_action::enter:
            {
                // машина могла приехать и сразу уехать без ожидания, тогда её
                // в очереди нет, но на дорогу она всё равно выезжает
                const std::size_t position = queue_position(waiting_, event.direction, event.id);
                if (position < waiting_.size())
                {
                    waiting_.erase(waiting_.begin() + static_cast<std::ptrdiff_t>(position));
                }

                double leave_time = 0;
                const auto known = data_.car_leave_times.find(event.id);
                if (known != data_.car_leave_times.end())
                {
                    leave_time = known->second;
                }
                else
                {
                    // отбытие не попало в лог — едем типовой длительности
                    leave_time = event.time + data_.default_passage_time;
                }

                moving_.push_back({event.id, event.direction, event.time, leave_time});
                break;
            }

            case trace::car_action::leave:
                drop_from_road(event.id);
                break;
        }
    }

    void scene::apply(const trace::light_event& event)
    {
        phase_ = event.to;
    }

    void scene::drop_from_queue(const char direction)
    {
        const auto found = std::find_if(waiting_.begin(), waiting_.end(),
                                        [direction](const waiting_car& car)
                                        { return car.direction == direction; });

        if (found != waiting_.end())
        {
            waiting_.erase(found);
        }
    }

    void scene::drop_from_road(const int id)
    {
        const auto found = std::find_if(moving_.begin(), moving_.end(),
                                        [id](const moving_car& car) { return car.id == id; });

        if (found != moving_.end())
        {
            moving_.erase(found);
        }
    }
}
