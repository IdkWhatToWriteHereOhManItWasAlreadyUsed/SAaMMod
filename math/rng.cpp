#include "rng.h"
#include <cmath>

namespace math
{
    rng::rng(const unsigned seed)
        : state_(seed == 0 ? 1u : seed)
    {
    }

    double rng::random()
    {
        constexpr unsigned m = (1u << 31) - 1;   // 2^31 - 1
        constexpr unsigned a = 185852;
        state_ = (state_ * a) % m;
        return static_cast<double>(state_) / m;
    }

    double rng::uniform(double a, double b)
    {
        return a + random() * (b - a);
    }

    double rng::exponential(const double frequency)
    {
        double u;
        do
        {
            u = rng::random();
        }
        while (u < 1e-10);
        return -std::log(u) / frequency;
    }

    double rng::normal(const double mean, const double sigma)
    {
        double sum = -6.0;
        for (int i = 0; i < 12; ++i)
        {
            sum += random();
        }
        return mean + sigma * sum;
    }
}