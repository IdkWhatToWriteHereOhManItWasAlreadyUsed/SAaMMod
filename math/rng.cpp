#include "rng.h"

#include <cmath>
#include <cstdint>

namespace math
{
    namespace
    {
        std::uint64_t splitmix64(std::uint64_t& x)
        {
            std::uint64_t z = (x += 0x9E3779B97F4A7C15ULL);
            z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
            z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
            return z ^ (z >> 31);
        }

        std::uint64_t xorshift64star(std::uint64_t& x)
        {
            x ^= x >> 12;
            x ^= x << 25;
            x ^= x >> 27;
            return x * 0x2545F4914F6CDD1DULL;
        }
    }

    rng::rng(const unsigned seed)
        : s_(0)
    {
        auto tmp = static_cast<std::uint64_t>(seed);
        s_ = splitmix64(tmp);
        if (s_ == 0) { s_ = 0x9E3779B97F4A7C15ULL; }
    }

    double rng::random()
    {
        const std::uint64_t v = xorshift64star(s_);
        return static_cast<double>(v >> 11) * 0x1.0p-53;
    }

    double rng::uniform(double a, double b)
    {
        return a + (b - a) * random();
    }

    double rng::exponential(const double frequency)
    {
        double u;
        do { u = random(); } while (u < 1e-10);
        return -std::log(u) / frequency;
    }

    double rng::normal(const double mean, const double sigma)
    {
        double sum = 0.0;
        for (int i = 0; i < 12; ++i) { sum += random(); }
        return mean + sigma * (sum - 6.0);
    }
}