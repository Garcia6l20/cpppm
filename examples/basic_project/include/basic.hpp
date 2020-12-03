#pragma once

#include <string>

#ifndef _MSC_VER
#define BASIC_API extern
#else
#ifdef BASIC_DLL_EXPORT
#define BASIC_API __declspec(dllexport)
#else
#define BASIC_API __declspec(dllimport)
#endif
#endif

namespace basic {
BASIC_API void say_hello(const std::string&);
}
