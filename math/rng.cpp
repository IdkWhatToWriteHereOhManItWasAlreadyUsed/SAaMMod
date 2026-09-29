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
        constexpr std::uint64_t m = (1ull << 31) - 1;   // 2^31 - 1
        constexpr std::uint64_t a = 185852;

        // умножение state_*a требует 64 бит — в 32-битном unsigned оно
        // переполнялось, и генератор схлопывался в короткий цикл
        state_ = static_cast<unsigned>((static_cast<std::uint64_t>(state_) * a) % m);
        return std::abs(static_cast<double>(state_));
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
