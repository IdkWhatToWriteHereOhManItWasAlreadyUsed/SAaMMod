#pragma once

namespace runner
{
    class i_runner
    {
    public:
        virtual ~i_runner() = default;
        virtual void simulate() = 0;
    };
}