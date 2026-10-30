#include "drain_run.h"

namespace runner
{
    bool drain_run::end_of_run()
    {
        if (!is_empty() && is_active())
        {
            return false;
        }

        if (!is_halted_)
        {
            model_->stop(*this);
            is_halted_ = true;
        }

        return is_empty();
    }

    void drain_run::finish_run()
    {
    }
}
