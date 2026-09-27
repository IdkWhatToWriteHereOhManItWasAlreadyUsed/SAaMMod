// mock_resource.h
#pragma once

#include <memory>
#include <queue>

#include "mock_agent.h"

namespace test
{
    // Ресурс с ограниченной вместимостью и очередью ожидания.
    class mock_resource
    {
    public:
        explicit mock_resource(int capacity)
            : capacity_(capacity)
            , free_(capacity)
        {}

        int capacity() const { return capacity_; }
        int free() const { return free_; }
        bool is_free() const { return free_ > 0; }

        void use() { --free_; }
        void release() { ++free_; }

        void push(std::shared_ptr<mock_agent> agent)
        {
            queue_.push(agent);
        }

        std::shared_ptr<mock_agent> pop()
        {
            if (queue_.empty()) return nullptr;
            auto agent = queue_.front();
            queue_.pop();
            return agent;
        }

        bool queue_empty() const { return queue_.empty(); }
        int queue_size() const { return static_cast<int>(queue_.size()); }

    private:
        int capacity_;
        int free_;
        std::queue<std::shared_ptr<mock_agent>> queue_;
    };
}
