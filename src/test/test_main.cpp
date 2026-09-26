#include "mock_runner.h"

int main()
{
    test::mock_runner runner(60.0);
    runner.simulate();
    return 0;
}