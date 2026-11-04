// Opaque base paint for a projected scene. The original faces, ink and transparent
// shells are painted above these paths. Coordinates are in the same frame as the
// visible-face renderer: two scene units per SVG unit, two SVG units per point.
#include "clipper2/clipper.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace {
using namespace Clipper2Lib;
constexpr double units_per_svg = 1000.0;
constexpr double inset = 0.6 * units_per_svg;
constexpr double tolerance = 0.15 * units_per_svg;

struct Placement {
    Paths64 triangles;
    std::array<std::map<int, double>, 3> channel_weights;
    double total_area = 0;
    double weighted_depth = 0;
};

int64_t coordinate(double value) {
    double scaled = value * (units_per_svg / 2.0);
    if (!std::isfinite(scaled) || std::abs(scaled) > (int64_t{1} << 52))
        throw std::runtime_error("Underpaint coordinate out of range");
    return std::llround(scaled);
}

std::string base_color(const Placement& part) {
    std::ostringstream result;
    result << '#' << std::hex << std::setfill('0');
    for (const auto& weights : part.channel_weights) {
        double sum = 0;
        for (const auto& [value, weight] : weights) {
            sum += weight;
            if (sum * 2 >= part.total_area) {
                result << std::setw(2) << value;
                break;
            }
        }
    }
    return result.str();
}
}

// Called by the native polygon tool after projection. Its SVG fragment is
// consumed only when the caller requests an underpaint pass.
void write_opaque_underpaint(const char* scene_file, const char* mask_file) {
    using namespace Clipper2Lib;
    std::ifstream input(scene_file);
    int width, height, red, green, blue, count;
    if (!(input >> width >> height >> red >> green >> blue >> count) || count < 0)
        throw std::runtime_error("Invalid underpaint scene header");

    std::map<int, Placement> parts;
    for (int index = 0; index < count; ++index) {
        int id;
        std::array<double, 3> rgb, depths;
        double alpha;
        if (!(input >> id >> rgb[0] >> rgb[1] >> rgb[2] >> alpha))
            throw std::runtime_error("Invalid underpaint triangle header");
        Path64 triangle;
        for (double& depth : depths) {
            double x, y;
            if (!(input >> x >> y >> depth) || !std::isfinite(depth))
                throw std::runtime_error("Invalid projected vertex");
            triangle.emplace_back(coordinate(x), coordinate(y));
        }
        if (!std::isfinite(alpha) || alpha < 0 || alpha > 1)
            throw std::runtime_error("Invalid underpaint opacity");
        if (alpha < 0.999999) continue;
        double area = Area(triangle);
        if (area == 0) continue;
        if (area < 0) std::reverse(triangle.begin(), triangle.end());
        area = std::abs(area);
        auto& part = parts[id];
        part.triangles.push_back(std::move(triangle));
        part.total_area += area;
        part.weighted_depth += area * (depths[0] + depths[1] + depths[2]) / 3;
        for (size_t channel = 0; channel < rgb.size(); ++channel) {
            double value = rgb[channel];
            if (!std::isfinite(value) || value < 0 || value > 255)
                throw std::runtime_error("Invalid underpaint color");
            part.channel_weights[channel][std::lround(value)] += area;
        }
    }

    std::vector<const Placement*> order;
    for (const auto& entry : parts) order.push_back(&entry.second);
    std::stable_sort(order.begin(), order.end(), [](const Placement* a, const Placement* b) {
        return a->weighted_depth / a->total_area < b->weighted_depth / b->total_area;
    });

    std::ofstream out(mask_file);
    out << std::fixed << std::setprecision(3) << "<g xmlns=\"http://www.w3.org/2000/svg\">";
    size_t count_masks = 0;
    for (const auto* part : order) {
        auto footprint = Union(part->triangles, FillRule::NonZero);
        auto inner = InflatePaths(footprint, -inset, JoinType::Bevel, EndType::Polygon);
        auto shape = SimplifyPaths(inner, tolerance);
        bool opened = false;
        for (const auto& path : shape) {
            if (path.size() < 3) continue;
            if (!opened) {
                out << "<path fill=\"" << base_color(*part) << "\" d=\"";
                opened = true;
            }
            for (size_t i = 0; i < path.size(); ++i)
                out << (i ? 'L' : 'M') << path[i].x / units_per_svg << ',' << path[i].y / units_per_svg;
            out << 'Z';
        }
        if (opened) { out << "\"/>"; ++count_masks; }
    }
    out << "</g>\n";
    out.close();
    if (!out) throw std::runtime_error("Cannot write opaque underpaint paths");
    std::cout << "{\"placement_masks\":" << count_masks
              << ",\"inset_svg_units\":" << inset / units_per_svg
              << ",\"simplification_svg_units\":" << tolerance / units_per_svg << "}\n";
}
