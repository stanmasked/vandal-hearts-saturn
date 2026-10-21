#pragma once
#include "vh/battle.hpp"
#include <istream>

namespace vh {
// Stage68: parses unverified, strictly numeric, row-major terrain metadata.
// Does NOT populate units, battle rules or authenticate the Saturn source.
// Throws std::invalid_argument if any record is malformed or incomplete.
Battle load_unverified_terrain(std::istream& source);
} // namespace vh
