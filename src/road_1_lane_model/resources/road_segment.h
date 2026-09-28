#pragma once

#include <cmath>
#include <vector>
#include <memory>

#include <road_1_lane_model/agents/car.h>

namespace resources
{
    class road_segment
    {
    public:
        explicit road_segment(double_t passage_time, double_t cars_interval);

        void reset();

        void push(char direction, std::shared_ptr<agents::car> car);
        void push_front(char direction, std::shared_ptr<agents::car> car);
        std::shared_ptr<agents::car> pop(char direction);

        // Машина выведена из очереди и ждёт cars_interval до въезда: в очереди
        // она формально остаётся, поэтому эти машины входят в queue_size().
        void detach(char direction, const std::shared_ptr<agents::car>& car);
        void attach(char direction, const std::shared_ptr<agents::car>& car);

        bool queue_empty(char direction) const;
        std::size_t queue_size(char direction) const;

        bool is_free() const;
        void enter(double_t time);
        void exit();

        double_t passage_time() const;
        double_t cars_interval() const;
        double_t last_car_enter_time() const;
        int capacity() const;

    private:
        std::vector<std::shared_ptr<agents::car>>& queue(char direction);
        const std::vector<std::shared_ptr<agents::car>>& queue(const char direction) const;

        double_t passage_time_;
        double_t cars_interval_;
        double_t last_car_enter_time_ = 0;
        int capacity_;
        int cars_on_segment_ = 0;
        std::size_t waiting_slot_a_ = 0;
        std::size_t waiting_slot_b_ = 0;
        std::vector<std::shared_ptr<agents::car>> queue_a_;
        std::vector<std::shared_ptr<agents::car>> queue_b_;
    };
}