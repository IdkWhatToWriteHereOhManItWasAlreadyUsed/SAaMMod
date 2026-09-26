#pragma once

namespace runner
{
    class i_agent
    {
    public:
        virtual int id() const = 0;
        virtual ~i_agent() = default;
    };
}