#include <basic.hpp>

int main(int argc, char** argv) {
    std::string who = DEFAULT_WHO;
    if (argc > 1)
        who = argv[1];
    basic::say_hello(who);
    return 0;
}