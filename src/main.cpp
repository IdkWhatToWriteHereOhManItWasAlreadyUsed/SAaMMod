#include "road_1_lane_model/road_1_lane_model.h"
#include "simple_runner/simple_runner.h"

int main()
{
    const auto model = std::make_shared<road_1_lane_model>(road_1_lane_model::config("/home/dmitry/CLionProjects/SAiMMOD_Lab2/lab2/Lab2_Code/config.json"));
    simple_runner runner(model, 1000.0);
    runner.simulate();
    return 0;
}