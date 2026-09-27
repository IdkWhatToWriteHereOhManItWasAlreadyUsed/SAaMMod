#pragma once
#include <cmath>

namespace math
{
    class rng
    {
    public:
        explicit rng(unsigned seed = 0);

        double_t random();
        double_t uniform(double a, double b);
        double_t exponential(double frequency);
        double_t normal(double mean, double sigma);

    private:
        unsigned state_;
    };
}
