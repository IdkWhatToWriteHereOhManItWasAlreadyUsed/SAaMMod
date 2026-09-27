// mock_agent.h
#pragma once

#include "i_agent.h"

namespace test
{
    // Простейший агент: у него есть только идентификатор.
    class mock_agent : public runner::i_agent
    {
    public:
        explicit mock_agent(int id) : id_(id) {}

        int id() const override { return id_; }

    private:
        int id_;
    };
}
