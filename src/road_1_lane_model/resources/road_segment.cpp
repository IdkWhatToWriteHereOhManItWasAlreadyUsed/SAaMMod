#include "road_segment.h"
#include "road_1_lane_model/agents/car.h"

namespace resources
{
    road_segment::road_segment(double_t passage_time, double_t cars_interval)
     : passage_time_(passage_time)
     , cars_interval_(cars_interval)
     , capacity_(static_cast<int>(passage_time / cars_interval))
    {
    }

    void road_segment::reset()
    {
        cars_on_segment_ = 0;
        queue_a_.clear();
        queue_b_.clear();
    }

    bool road_segment::is_free() const
    {
        return cars_on_segment_ < capacity_;
    }

    void road_segment::enter(double_t time)
    {
        last_car_enter_time_ = time;
        ++cars_on_segment_;
    }

    double_t road_segment::last_car_enter_time() const
    {
        return last_car_enter_time_;
    }

    void road_segment::exit()
    {
        --cars_on_segment_;
    }

    int road_segment::capacity() const
    {
        return capacity_;
    }

    void road_segment::push(char direction, std::shared_ptr<agents::car> car)
    {
        queue(direction).push_back(car);
    }

    void road_segment::push_front(char direction, std::shared_ptr<agents::car> car)
    {
        queue(direction).insert(queue(direction).begin(), car);
    }

    std::shared_ptr<agents::car> road_segment::pop(char direction)
    {
        auto& q = queue(direction);
        if (q.empty())
        {
            return nullptr;
        }
        auto car = q.front();
        q.erase(q.begin());
        return car;
    }

    bool road_segment::queue_empty(char direction) const
    {
        return queue(direction).empty();
    }

    std::size_t road_segment::queue_size(char direction) const
    {
        return queue(direction).size();
    }

    std::vector<std::shared_ptr<agents::car>>& road_segment::queue(char direction)
    {
        return (direction == 'A') ? queue_a_ : queue_b_;
    }

    const std::vector<std::shared_ptr<agents::car>>& road_segment::queue(const char direction) const
    {
        return (direction == 'A') ? queue_a_ : queue_b_;
    }

    double_t road_segment::cars_interval() const {return cars_interval_; }
    double_t road_segment::passage_time() const { return passage_time_; }
}