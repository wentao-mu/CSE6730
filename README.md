# cse6730

Assesses how pressing intensity and fatigue affect chance creation.

## Member C Deliverable Summary

Member C completed the pressing and fatigue subsystem for the soccer
simulation. The implementation adds three pressing levels (`low`,
`medium`, `high`) at the team level and models fatigue as a scalar from
0 to 1 that increases linearly over match steps, with halftime recovery
included. Effective pressing now decreases as fatigue rises, so teams
that press aggressively early in the match lose some defensive pressure
later on.

The pressing module applies these fatigue-adjusted effects to turnover
and ball-recovery probabilities, and fatigue also slightly reduces
attacking execution to reflect lower passing and shooting sharpness under
load. This work is integrated into the engine loop, so fatigue is
updated automatically each simulation step and carried through the full
match state.

All shared tuning values were centralized in
`config/default_params.yaml`, including pressing multipliers, fatigue
accumulation rates, halftime recovery, and penalty curve parameters.
Targeted unit tests were added for fatigue accumulation, fatigue-based
pressing decay, pressing probability adjustments, and engine
integration. The interface is now stable and ready to plug into the
calibrated transition matrix once that module is finalized.
