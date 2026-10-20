#include "vh/battle.hpp"
#include "vh/smoke.hpp"

#include <cassert>
#include <stdexcept>

static int parse(int argc, const char* const argv[]) {
    return vh::smoke_frames_from_args(argc, argv);
}

int main() {
    assert(vh::smoke_training_scene_ready(vh::Battle::training()));
    vh::Battle empty(8, 8);
    assert(!vh::smoke_training_scene_ready(empty));
    const char* normal[] = {"demo"};
    assert(parse(1, normal) == 0);
    const char* one[] = {"demo", "--smoke-frames=1"};
    assert(parse(2, one) == 1);
    const char* max[] = {"demo", "--smoke-frames=600"};
    assert(parse(2, max) == 600);
    const char* ignore[] = {"demo", "--other-switch"};
    assert(parse(2, ignore) == 0);
    const char* invalids[] = {"--smoke-frames=0", "--smoke-frames=601",
                             "--smoke-frames=-5", "--smoke-frames=1x",
                             "--smoke-frames="};
    for (const auto* invalid : invalids) {
        const char* args[] = {"demo", invalid};
        bool caught = false;
        try { (void)parse(2, args); }
        catch (const std::invalid_argument&) { caught = true; }
        assert(caught);
    }
    const char* duplicate[] = {"demo", "--smoke-frames=5", "--smoke-frames=10"};
    bool caught = false;
    try { (void)parse(3, duplicate); }
    catch (const std::invalid_argument&) { caught = true; }
    assert(caught);
    return 0;
}
