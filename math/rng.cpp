#include "rng.h"

#include <cmath>
#include <cstdint>
#include <random>
#include <bits/this_thread_sleep.h>

namespace math
{
    rng::rng(const unsigned seed)
        : state_(seed == 0 ? 1u : seed)
    {
    }

    double rng::random()
    {
        return rand();
    }

    double rng::uniform(double a, double b)
    {
        return std::abs(a + random() * (b - a));
    }

    double rng::exponential(const double frequency)
    {
        double u;
        do
        {
            u = rng::random();
        }
        while (u < 1e-10);
        return std::abs(-std::log(u) / frequency);
    }

    double rng::normal(const double mean, const double sigma)
    {
        double sum = -6.0;
        for (int i = 0; i < 12; ++i)
        {
            sum += random();
        }
        return std::abs(mean + sigma * sum);
    }
}
