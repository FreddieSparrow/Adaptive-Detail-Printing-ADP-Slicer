#ifndef __FILAMENT_MATCHER_HPP__
#define __FILAMENT_MATCHER_HPP__

#include <string>

namespace Slic3r {

class PresetCollection;

// Shared filament-to-preset matching for all printer agents.
//
// Each agent populates a FilamentMatchInput with whatever data the printer
// provides, then calls FilamentMatcher::resolve() to find the best matching
// OrcaSlicer filament preset.  Tiers that lack data are skipped automatically.
//
// Tier cascade (most specific -> least specific):
//
//   Tier 1: {prefix}_{FilamentVendor}_{FilamentName}_{ColorHex}
//           e.g. QD_3_Acme_Inc_PLA_Plus_FAFAFA
//
//   Tier 2: {prefix}_{FilamentVendor}_{FilamentName}
//           e.g. QD_3_Acme_Inc_PLA_Plus
//
//   Tier 3: {prefix}_{vendor_num}_{filament_idx}
//           e.g. QD_3_7_52
//
//   Tier 4: filament_id_by_type(tray_type)
//           Searches installed presets by material type, e.g. "PLA"
//
//   Tier 5: map_type_to_generic_id(tray_type)
//           Static fallback to OrcaFilamentLibrary IDs, e.g. "PLA" -> "OGFL99"
//
// The prefix encodes both the agent and the printer model so that filament
// profiles can target a specific printer.  Examples:
//   QIDI X-Max 4:   prefix = "QD_3"
//   Snapmaker J1:   prefix = "SM_J1"
//   Generic Klipper: prefix = "MK"
//
// An agent with only tray_type (e.g. "PLA") skips tiers 1-3 and still gets
// a correct match via tiers 4/5.  This is the current behavior for Moonraker
// and Snapmaker agents.

struct FilamentMatchInput {
    std::string prefix;            // Agent + printer model prefix, e.g. "QD_3", "SM_J1", "MK"
    std::string vendor_name;       // Sanitized filament vendor name, e.g. "Acme_Inc"
    std::string filament_name;     // Sanitized filament name, e.g. "PLA_Plus"
    std::string color_hex;         // Color hex without #, e.g. "FAFAFA"
    int         vendor_type = -1;  // Numeric vendor ID
    int         filament_idx = -1; // Numeric filament index
    std::string tray_type;         // Base material type for fallback, e.g. "PLA"
};

namespace FilamentMatcher {

// Resolve the best matching filament preset ID for the given input.
// Tries tiers 1-5 from most specific to least specific, skipping tiers
// where required fields are missing.
std::string resolve(const FilamentMatchInput& input);

// Sanitize a filament vendor or filament name for use in preset IDs.
// Non-alphanumeric characters become underscores; consecutive underscores
// are collapsed and trailing underscores are stripped.
//   "Acme Inc"     -> "Acme_Inc"      (filament vendor name)
//   "PLA Plus"     -> "PLA_Plus"      (filament name)
//   "PLA-AERO"     -> "PLA_AERO"      (filament name)
//   "TPU-AERO 64D" -> "TPU_AERO_64D"  (filament name)
std::string sanitize_for_id(const std::string& name);

// Check whether any visible, compatible preset has the given filament_id.
// Matches both system base presets and user presets with custom filament_id.
// Uses case-insensitive comparison so profile authors don't need to match
// exact casing from the printer's filament config.
bool has_visible_preset(const PresetCollection& filaments, const std::string& filament_id);

// Map a filament type string (e.g. "PLA", "ABS") to an OrcaFilamentLibrary
// generic preset ID (e.g. "OGFL99").  Used as the last-resort fallback when
// no preset bundle is available.
std::string map_type_to_generic_id(const std::string& filament_type);

} // namespace FilamentMatcher
} // namespace Slic3r

#endif
