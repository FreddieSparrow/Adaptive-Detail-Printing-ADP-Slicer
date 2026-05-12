#include "FilamentMatcher.hpp"
#include "libslic3r/Preset.hpp"
#include "libslic3r/PresetBundle.hpp"
#include "slic3r/GUI/GUI_App.hpp"

#include <boost/algorithm/string.hpp>
#include <boost/log/trivial.hpp>
#include <algorithm>
#include <cctype>

namespace Slic3r {
namespace FilamentMatcher {

// Sanitize filament vendor or filament name for use in preset IDs.
// "Acme Inc" -> "Acme_Inc", "PLA Plus" -> "PLA_Plus", "PLA-AERO" -> "PLA_AERO"
std::string sanitize_for_id(const std::string& name)
{
    std::string result;
    result.reserve(name.size());
    for (char c : name) {
        if (std::isalnum(static_cast<unsigned char>(c)))
            result.push_back(c);
        else if (!result.empty() && result.back() != '_')
            result.push_back('_');
    }
    if (!result.empty() && result.back() == '_')
        result.pop_back();
    return result;
}

bool has_visible_preset(const PresetCollection& filaments, const std::string& filament_id)
{
    for (const auto& p : filaments.get_presets()) {
        if (p.is_visible && p.is_compatible
            && boost::iequals(p.filament_id, filament_id))
            return true;
    }
    return false;
}

static std::string trim_and_upper(const std::string& input)
{
    std::string result = input;
    boost::trim(result);
    std::transform(result.begin(), result.end(), result.begin(),
                   [](unsigned char c) { return static_cast<char>(std::toupper(c)); });
    return result;
}

std::string map_type_to_generic_id(const std::string& filament_type)
{
    const std::string upper = trim_and_upper(filament_type);

    // PLA variants
    if (upper == "PLA")           return "OGFL99";
    if (upper == "PLA-CF")        return "OGFL98";
    if (upper == "PLA SILK" || upper == "PLA-SILK") return "OGFL96";
    if (upper == "PLA HIGH SPEED" || upper == "PLA-HS" || upper == "PLA HS") return "OGFL95";

    // ABS/ASA variants
    if (upper == "ABS")           return "OGFB99";
    if (upper == "ASA")           return "OGFB98";

    // PETG/PET variants
    if (upper == "PETG" || upper == "PET") return "OGFG99";
    if (upper == "PCTG")          return "OGFG97";

    // PA/Nylon variants
    if (upper == "PA" || upper == "NYLON") return "OGFN99";
    if (upper == "PA-CF")         return "OGFN98";
    if (upper == "PPA" || upper == "PPA-CF") return "OGFN97";
    if (upper == "PPA-GF")        return "OGFN96";

    // PC variants
    if (upper == "PC")            return "OGFC99";

    // PP/PE variants
    if (upper == "PE")            return "OGFP99";
    if (upper == "PP")            return "OGFP97";

    // Support materials
    if (upper == "PVA")           return "OGFS99";
    if (upper == "HIPS")          return "OGFS98";
    if (upper == "BVOH")          return "OGFS97";

    // TPU variants
    if (upper == "TPU")           return "OGFU99";

    // Other materials
    if (upper == "EVA")           return "OGFR99";
    if (upper == "PHA")           return "OGFR98";
    if (upper == "COPE")          return "OGFLC99";
    if (upper == "SBS")           return "OFLSBS99";

    return UNKNOWN_FILAMENT_ID;
}

// Multi-tier preset matching: most specific to least specific.
// Agents build their prefix from agent ID + model (e.g. "QD_3", "SM_J1").
//
// Example with prefix="QD_3" (QIDI X-Max 4):
//
//   [fila52]               filament = PLA Plus
//   [colordict]            52       = #FAFAFA
//   [vendor_list]          7        = Acme Inc
//
//   Tier 1: QD_3_Acme_Inc_PLA_Plus_FAFAFA  (filament vendor + name + color)
//   Tier 2: QD_3_Acme_Inc_PLA_Plus         (filament vendor + name)
//   Tier 3: QD_3_7_52                      (numeric vendor + filament index)
//   Tier 4: filament_id_by_type("PLA")
//   Tier 5: map_type_to_generic_id("PLA") -> "OGFL99"
std::string resolve(const FilamentMatchInput& input)
{
    auto* bundle = GUI::wxGetApp().preset_bundle;

    const bool have_prefix = !input.prefix.empty();
    const bool have_names  = !input.vendor_name.empty() && !input.filament_name.empty();

    BOOST_LOG_TRIVIAL(info) << "FilamentMatcher::resolve: tray_type=\"" << input.tray_type
                            << "\" prefix=\"" << input.prefix << "\"";

    // Track whether the printer gave us enough data to attempt precise tiers.
    // If it did but none matched, we warn the user so they can create a
    // filament profile with one of the candidate IDs.
    bool tried_precise = false;
    std::string tier1_id, tier2_id, tier3_id;

    if (bundle && have_prefix && have_names) {
        // Tier 1: {prefix}_{FilamentVendor}_{FilamentName}_{ColorHex}
        // e.g. QD_3_Acme_Inc_PLA_Plus_FAFAFA
        // Matches a preset for a specific filament vendor + material + color.
        if (!input.color_hex.empty()) {
            tier1_id = input.prefix + "_" + input.vendor_name + "_"
                     + input.filament_name + "_" + input.color_hex;
            tried_precise = true;
            BOOST_LOG_TRIVIAL(info) << "  Tier 1: trying filament_id=\"" << tier1_id << "\"";
            if (has_visible_preset(bundle->filaments, tier1_id)) {
                BOOST_LOG_TRIVIAL(info) << "  -> matched at Tier 1";
                return tier1_id;
            }
        }

        // Tier 2: {prefix}_{FilamentVendor}_{FilamentName}
        // e.g. QD_3_Acme_Inc_PLA_Plus
        // Matches any color of a specific filament vendor + material.
        tier2_id = input.prefix + "_" + input.vendor_name + "_" + input.filament_name;
        tried_precise = true;
        BOOST_LOG_TRIVIAL(info) << "  Tier 2: trying filament_id=\"" << tier2_id << "\"";
        if (has_visible_preset(bundle->filaments, tier2_id)) {
            BOOST_LOG_TRIVIAL(info) << "  -> matched at Tier 2";
            return tier2_id;
        }
    }

    // Tier 3: {prefix}_{vendor_num}_{filament_idx}
    // e.g. QD_3_7_52
    // Numeric lookup using raw vendor and filament indices from the printer.
    // This is the format used by existing QIDI filament profiles.
    if (have_prefix && input.filament_idx > 0) {
        tier3_id = input.prefix + "_" + std::to_string(input.vendor_type) + "_"
                 + std::to_string(input.filament_idx);
        tried_precise = true;
        BOOST_LOG_TRIVIAL(info) << "  Tier 3: trying filament_id=\"" << tier3_id << "\"";
        if (!bundle || has_visible_preset(bundle->filaments, tier3_id)) {
            BOOST_LOG_TRIVIAL(info) << "  -> matched at Tier 3";
            return tier3_id;
        }
    }

    // If the printer reported enough data for precise matching but none of
    // the candidate IDs matched an installed preset, warn the user.  This
    // tells them exactly what filament_id to set in a custom filament profile
    // to get an exact match next time.
    //
    // We only warn when precise tiers were attempted -- agents that only
    // provide tray_type (e.g. generic Moonraker, Snapmaker) can't do any
    // better, so warning them would be noise.
    if (tried_precise) {
        std::string candidates;
        if (!tier1_id.empty())
            candidates += "\"" + tier1_id + "\", ";
        if (!tier2_id.empty())
            candidates += "\"" + tier2_id + "\", ";
        if (!tier3_id.empty())
            candidates += "\"" + tier3_id + "\"";
        BOOST_LOG_TRIVIAL(warning)
            << "FilamentMatcher: no precise preset found for \""
            << input.filament_name << "\" (type " << input.tray_type
            << ").  Falling back to generic type match.  "
            << "To get an exact match, create a filament profile with "
            << "filament_id set to one of: " << candidates;
    }

    // Tier 4: preset bundle type-based lookup
    // Searches installed presets for one whose filament_type matches tray_type
    // (e.g. "PLA").  This is the path taken by agents that only report a material
    // type without vendor/color data (Moonraker, Snapmaker today).
    if (bundle && !input.tray_type.empty()) {
        std::string id = bundle->filaments.filament_id_by_type(input.tray_type);
        BOOST_LOG_TRIVIAL(info) << "  Tier 4: filament_id_by_type(\"" << input.tray_type
                                << "\") -> \"" << id << "\"";
        if (!id.empty() && id != UNKNOWN_FILAMENT_ID) {
            BOOST_LOG_TRIVIAL(info) << "  -> matched at Tier 4";
            return id;
        }
    }

    // Tier 5: static generic ID mapping
    // Last resort when no preset bundle is loaded.  Maps type strings to
    // OrcaFilamentLibrary IDs, e.g. "PLA" -> "OGFL99", "ABS" -> "OGFB99".
    if (!input.tray_type.empty()) {
        std::string id = map_type_to_generic_id(input.tray_type);
        BOOST_LOG_TRIVIAL(info) << "  Tier 5: map_type_to_generic_id(\"" << input.tray_type
                                << "\") -> \"" << id << "\"";
        return id;
    }

    BOOST_LOG_TRIVIAL(info) << "  -> no match, returning UNKNOWN";
    return UNKNOWN_FILAMENT_ID;
}

} // namespace FilamentMatcher
} // namespace Slic3r
