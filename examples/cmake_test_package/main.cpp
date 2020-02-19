#include <xdev/xdev.hpp>
#include <test-object.hpp>

#include <cassert>

int main(int argc, char** argv) {
    auto d = xdev::XDict{
        {"hello", "conan"}
    };
    std::cout << d.toString() << std::endl;
    auto v = xdev::XVariant::FromJSON(R"({
        "hello": "conan"
    })");
    std::cout << v.toString() << std::endl;
    auto obj = xdev::XObjectBase::Create<TestObject>();
    assert(obj->call("whatIsTheAnswer") == 42);
    return 0;
}
