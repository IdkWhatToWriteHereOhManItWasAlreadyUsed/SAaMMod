cmake_minimum_required(VERSION 3.20)
project(runner)

set(CMAKE_CXX_STANDARD 20)

add_library(${PROJECT_NAME}
        # .cpp
        impl/run_base.cpp
        # headers (для IDE)
        public/event.h
        public/i_agent.h
        public/i_model.h
        public/i_run.h
        public/i_runner.h
        public/run_base.h
)

target_include_directories(${PROJECT_NAME} PUBLIC
        "${CMAKE_CURRENT_SOURCE_DIR}/public"
)

target_include_directories(${PROJECT_NAME} PRIVATE
        "${CMAKE_CURRENT_SOURCE_DIR}"
        "${CMAKE_CURRENT_SOURCE_DIR}/impl"
)