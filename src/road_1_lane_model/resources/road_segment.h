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

        bool queue_empty(char direction) const;
        std::size_t queue_size(char direction) const;

        bool is_free() const;
        void enter();
        void exit();

        double_t passage_time() const;
        double_t cars_interval() const;
        int capacity() const;

    private:
        std::vector<std::shared_ptr<agents::car>>& queue(char direction);
        const std::vector<std::shared_ptr<agents::car>>& queue(const char direction) const;

        double_t passage_time_;
        double_t cars_interval_;
        int capacity_;
        int cars_on_segment_ = 0;
        std::vector<std::shared_ptr<agents::car>> queue_a_;
        std::vector<std::shared_ptr<agents::car>> queue_b_;
    };
}