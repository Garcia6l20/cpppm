#include <fmt/format.h>
#include <generated/config.hpp>

int main() {
  fmt::print("-- generated at: {}\n", GENERATED_TIME);
}
