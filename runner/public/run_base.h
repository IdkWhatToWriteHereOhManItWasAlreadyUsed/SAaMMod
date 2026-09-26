#pragma once

#include <vector>
#include "i_model.h"
#include "i_run.h"

namespace runner
{
    class run_base : public i_run
    {
    public:
        explicit run_base(std::shared_ptr<i_model> model, const double_t run_time);
        virtual ~run_base() override = default;

        void run() override;

        double_t model_time() const override;
        i_model& model() override;
        void new_event(std::shared_ptr<i_agent> agent, handler_t handler, double time) override;
        void move_active_event(double dif_time, handler_t handler) override;
        void next_active_event(handler_t handler, std::shared_ptr<i_agent> agent) override;
        void delete_active_event() override;
        void delete_event(std::shared_ptr<i_agent> agent) override;

    protected:
        virtual bool end_of_run();
        virtual bool is_active();
        virtual bool is_empty();
        virtual double_t next_time(double_t base_time);
        void insert_event(const event& e);

        std::vector<event> events_;
        double_t model_time_ = 0;
        double_t run_time_;
        std::shared_ptr<i_model> model_;
        bool is_halted_ = false;
    };
}