#include <iostream>

#include "mock_runner.h"

int main()
{
    // capacity=1 -> очередь растёт: приход каждые 3 мин, обслуживание 4 мин.
    // capacity=2 -> очередь не образуется: обслуживание успевает за приходом.
    test::mock_runner runner(60.0, 1);

    std::cout << "=== run start ===\n";
    runner.simulate();
    std::cout << "=== run end ===\n";

    return 0;
}
