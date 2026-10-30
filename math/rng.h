#pragma once

#include <cstdint>

namespace math
{
    class rng
    {
    public:
        explicit rng(unsigned seed);

        double random();
        double uniform(double a, double b);
        double exponential(double frequency);
        double normal(double mean, double sigma);

    private:
        std::uint64_t s_;
    };
}