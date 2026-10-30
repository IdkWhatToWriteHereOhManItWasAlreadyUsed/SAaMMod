#pragma once
#include <cmath>

namespace math
{
    class rng
    {
    public:
        explicit rng(unsigned seed = 0);

        static double_t random();
        static double_t uniform(double a, double b);
        static double_t exponential(double frequency);
        static double_t normal(double mean, double sigma);

    private:
        unsigned state_;
    };
}
