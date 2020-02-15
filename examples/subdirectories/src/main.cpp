#include <iostream>

#include <ctti/type_id.hpp>

struct HelloCtti {};

int main(int, char**) {
    std::cout << ctti::type_id<HelloCtti>().name().cppstring() << "\n";
    return 0;
}
