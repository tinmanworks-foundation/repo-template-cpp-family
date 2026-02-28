#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

MODELS = [
    "lib",
    "exe",
    "engine-app",
    "workspace",
    "plugin-shared",
    "plugin-addon",
]
LANGS = ["c", "cpp"]


def project_id(name: str) -> str:
    return name.replace("-", "_").lower()


def project_title(name: str) -> str:
    return "".join(part.capitalize() for part in re.split(r"[-_]+", name))


def src_ext(lang: str) -> str:
    return "c" if lang == "c" else "cpp"


def header_ext(lang: str) -> str:
    return "h" if lang == "c" else "hpp"


def cmake_languages(lang: str) -> str:
    return "C CXX" if lang == "c" else "CXX"


def standard_block(lang: str) -> str:
    if lang == "c":
        return textwrap.dedent(
            """
            set(CMAKE_C_STANDARD 17)
            set(CMAKE_C_STANDARD_REQUIRED ON)
            set(CMAKE_C_EXTENSIONS OFF)

            # GTest is C++, so keep C++ available for tests in C projects.
            set(CMAKE_CXX_STANDARD 20)
            set(CMAKE_CXX_STANDARD_REQUIRED ON)
            set(CMAKE_CXX_EXTENSIONS OFF)
            """
        ).strip()
    return textwrap.dedent(
        """
        set(CMAKE_CXX_STANDARD 20)
        set(CMAKE_CXX_STANDARD_REQUIRED ON)
        set(CMAKE_CXX_EXTENSIONS OFF)
        """
    ).strip()


def write_file(root: Path, rel: str, content: str) -> None:
    target = root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content.rstrip() + "\n", encoding="utf-8")


def copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def copy_tree(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    shutil.copytree(src, dst, dirs_exist_ok=True)


def gtest_fetchcontent_block() -> str:
    return textwrap.dedent(
        """
        include(FetchContent)
        FetchContent_Declare(
          googletest
          URL https://github.com/google/googletest/archive/refs/tags/v1.14.0.zip
        )
        set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
        FetchContent_MakeAvailable(googletest)

        include(GoogleTest)
        """
    ).strip()


def generated_ci_workflow() -> str:
    return textwrap.dedent(
        """
        name: CI (C/C++ CMake)

        on:
          push:
          pull_request:

        jobs:
          build:
            runs-on: ubuntu-latest

            steps:
              - uses: actions/checkout@v4

              - name: Toolchain doctor
                run: bash tools/setup/bootstrap.sh --doctor --non-interactive

              - name: Configure
                run: cmake --preset native-debug

              - name: Build
                run: cmake --build --preset native-debug

              - name: Test
                run: ctest --preset native-debug --output-on-failure
        """
    ).strip()


def cmake_presets() -> str:
    presets = {
        "version": 5,
        "cmakeMinimumRequired": {"major": 3, "minor": 20, "patch": 0},
        "configurePresets": [
            {
                "name": "native-debug",
                "displayName": "Native Debug",
                "binaryDir": "${sourceDir}/build/native-debug",
                "cacheVariables": {"CMAKE_BUILD_TYPE": "Debug"},
            },
            {
                "name": "native-release",
                "displayName": "Native Release",
                "binaryDir": "${sourceDir}/build/native-release",
                "cacheVariables": {"CMAKE_BUILD_TYPE": "Release"},
            },
            {
                "name": "ninja-debug",
                "displayName": "Ninja Debug",
                "generator": "Ninja",
                "binaryDir": "${sourceDir}/build/ninja-debug",
                "cacheVariables": {"CMAKE_BUILD_TYPE": "Debug"},
            },
            {
                "name": "ninja-release",
                "displayName": "Ninja Release",
                "generator": "Ninja",
                "binaryDir": "${sourceDir}/build/ninja-release",
                "cacheVariables": {"CMAKE_BUILD_TYPE": "Release"},
            },
        ],
        "buildPresets": [
            {"name": "native-debug", "configurePreset": "native-debug"},
            {"name": "native-release", "configurePreset": "native-release"},
            {"name": "ninja-debug", "configurePreset": "ninja-debug"},
            {"name": "ninja-release", "configurePreset": "ninja-release"},
        ],
        "testPresets": [
            {
                "name": "native-debug",
                "configurePreset": "native-debug",
                "output": {"outputOnFailure": True},
            },
            {
                "name": "native-release",
                "configurePreset": "native-release",
                "output": {"outputOnFailure": True},
            },
            {
                "name": "ninja-debug",
                "configurePreset": "ninja-debug",
                "output": {"outputOnFailure": True},
            },
            {
                "name": "ninja-release",
                "configurePreset": "ninja-release",
                "output": {"outputOnFailure": True},
            },
        ],
    }
    return json.dumps(presets, indent=2)


def common_files(name: str, model: str, lang: str, preset_choice: str) -> dict[str, str]:
    pid = project_id(name)
    pt = project_title(name)
    preset = "native-debug" if preset_choice == "native" else "ninja-debug"
    lang_note = "C" if lang == "c" else "C++"

    readme = f"""# {pt}

Generated from `repo-template-cpp-family` using model `{model}` and primary language `{lang}`.

## Status
- Stage: Draft | Active | Stable | Deprecated
- Owner: <Owner>
- License: <License Name>
- Visibility: Public | Private | Internal
- Reason: <Why this visibility level is correct>
- Promotion criteria to Public: <What must be true before public release>

## What This Project Is
- CMake-first starter for the `{model}` architecture.
- Primary compiled language is `{lang_note}`.
- Helper scripts in `tools/` may use other languages (for example Python) regardless of `--lang`.

## Quickstart

### Dependency doctor
#### macOS / Linux
```bash
bash tools/setup/bootstrap.sh --doctor --non-interactive
```

#### Windows (PowerShell)
```powershell
.\\tools\\setup\\bootstrap.ps1 --doctor --non-interactive
```

### Optional install mode
#### macOS / Linux
```bash
bash tools/setup/bootstrap.sh --install --with-optional --non-interactive
```

#### Windows (PowerShell)
```powershell
.\\tools\\setup\\bootstrap.ps1 --install --with-optional --non-interactive
```

### Configure / Build / Test
```bash
cmake --preset {preset}
cmake --build --preset {preset}
ctest --preset {preset} --output-on-failure
```

Ninja is optional and recommended. `native-*` presets work without Ninja.

## Repository Layout
- `docs/` project documentation
- `src/` and `include/` primary source/public headers
- `tests/` tests
- `examples/` runnable examples
- `tools/` helper scripts and environment setup

## Documentation
- [Overview](docs/overview.md)
- [Architecture](docs/architecture.md)
- [ADRs](docs/adr/)

## Contributing
See `CONTRIBUTING.md`.
"""

    return {
        ".gitignore": textwrap.dedent(
            """
            # Build artifacts
            build/
            out/
            bin/
            obj/
            .cache/

            # IDE/editor
            .idea/
            .vscode/
            *.swp

            # OS
            .DS_Store
            Thumbs.db

            # Generated/auxiliary
            compile_commands.json
            *.log
            """
        ).strip(),
        ".editorconfig": textwrap.dedent(
            """
            root = true

            [*]
            end_of_line = lf
            insert_final_newline = true
            charset = utf-8
            indent_style = space
            indent_size = 4
            trim_trailing_whitespace = true

            [*.md]
            trim_trailing_whitespace = false

            [*.{yml,yaml,json,cmake}]
            indent_size = 2

            [*.{c,cc,cpp,cxx,h,hh,hpp,hxx,ipp,tpp}]
            indent_size = 4
            """
        ).strip(),
        "LICENSE": textwrap.dedent(
            """
            Template License Placeholder

            Replace this file with the final license text before public release.
            """
        ).strip(),
        "CONTRIBUTING.md": textwrap.dedent(
            """
            # Contributing

            ## Branching
            - `master` stable branch
            - Feature branches: `feat/<topic>`
            - Fix branches: `fix/<topic>`

            ## Pull Requests
            - Keep PRs focused.
            - Update docs for behavior or architecture changes.
            - Keep CI green before merge.

            ## Commit Signing
            - Signed commits are required for release and protected branches.
            """
        ).strip(),
        "REPO_POLICY.md": textwrap.dedent(
            """
            # Repository Policy

            ## Visibility
            - Visibility: Public | Private | Internal
            - Reason: <Required>
            - Promotion criteria to Public: <Required>

            ## Standards
            - Keep repository structure doctrine-aligned.
            - Keep signed commit workflow enabled.
            - Keep generated artifacts out of version control.
            """
        ).strip(),
        "README.md": readme.strip(),
        "docs/overview.md": textwrap.dedent(
            f"""
            # Overview

            ## Purpose
            Describe the purpose of this `{model}` project.

            ## Scope
            Define what is in scope and explicitly out of scope.

            ## High-Level Behavior
            - Capability 1
            - Capability 2
            - Capability 3
            """
        ).strip(),
        "docs/architecture.md": textwrap.dedent(
            f"""
            # Architecture

            ## Model
            This repository uses the `{model}` model generated by `repo-template-cpp-family`.

            ## Components
            Describe core modules and dependencies.

            ## Data Flow
            1. Input enters the system.
            2. Domain logic processes it.
            3. Output is produced.
            """
        ).strip(),
        "docs/adr/0001-template.md": textwrap.dedent(
            """
            # ADR 0001: Adopt C/C++ CMake Family Template

            ## Status
            Accepted

            ## Context
            This project uses a standard template to reduce setup drift and improve maintainability.

            ## Decision
            Use `repo-template-cpp-family` and keep doctrine artifacts in-repo.

            ## Consequences
            - Faster onboarding
            - Predictable structure
            - Better automation compatibility
            """
        ).strip(),
        ".github/workflows/ci-cpp.yml": generated_ci_workflow(),
        "CMakePresets.json": cmake_presets(),
        "examples/.gitkeep": "",
        "tools/.gitkeep": "",
    }


def lib_model(name: str, lang: str) -> dict[str, str]:
    pid = project_id(name)
    pt = project_title(name)
    se = src_ext(lang)
    he = header_ext(lang)

    if lang == "c":
        header = f"""#pragma once

int {pid}_add(int a, int b);
"""
        source = f"""#include \"{pid}.{he}\"

int {pid}_add(int a, int b) {{
    return a + b;
}}
"""
        example = f"""#include <stdio.h>
#include \"{pid}.{he}\"

int main(void) {{
    printf(\"result=%d\\n\", {pid}_add(2, 3));
    return 0;
}}
"""
        test = f"""#include <gtest/gtest.h>
extern \"C\" {{
#include \"{pid}.{he}\"
}}

TEST({pt}Lib, AddsNumbers) {{
    EXPECT_EQ({pid}_add(2, 3), 5);
}}
"""
    else:
        header = f"""#pragma once

namespace {pid} {{
int add(int a, int b);
}}
"""
        source = f"""#include \"{pid}.{he}\"

namespace {pid} {{
int add(int a, int b) {{
    return a + b;
}}
}} // namespace {pid}
"""
        example = f"""#include <iostream>
#include \"{pid}.{he}\"

int main() {{
    std::cout << \"result=\" << {pid}::add(2, 3) << std::endl;
    return 0;
}}
"""
        test = f"""#include <gtest/gtest.h>
#include \"{pid}.{he}\"

TEST({pt}Lib, AddsNumbers) {{
    EXPECT_EQ({pid}::add(2, 3), 5);
}}
"""

    cmake = f"""cmake_minimum_required(VERSION 3.20)

project({pt}
  VERSION 0.1.0
  DESCRIPTION \"{pt} library model\"
  LANGUAGES {cmake_languages(lang)}
)

{standard_block(lang)}

include(CTest)

add_library(${{PROJECT_NAME}}
  src/{pid}.{se}
)

target_include_directories(${{PROJECT_NAME}}
  PUBLIC
    ${{CMAKE_CURRENT_SOURCE_DIR}}/include
)

add_executable(${{PROJECT_NAME}}_example
  examples/{pid}_example.{se}
)
target_link_libraries(${{PROJECT_NAME}}_example PRIVATE ${{PROJECT_NAME}})

if(BUILD_TESTING)
  add_subdirectory(tests)
endif()
"""

    tests_cmake = f"""{gtest_fetchcontent_block()}

add_executable(${{PROJECT_NAME}}_tests
  test_{pid}.cpp
)

target_link_libraries(${{PROJECT_NAME}}_tests
  PRIVATE
    ${{PROJECT_NAME}}
    GTest::gtest_main
)

gtest_discover_tests(${{PROJECT_NAME}}_tests)
"""

    return {
        "CMakeLists.txt": cmake.strip(),
        f"include/{pid}.{he}": header.strip(),
        f"src/{pid}.{se}": source.strip(),
        f"examples/{pid}_example.{se}": example.strip(),
        "tests/CMakeLists.txt": tests_cmake.strip(),
        f"tests/test_{pid}.cpp": test.strip(),
    }


def exe_model(name: str, lang: str) -> dict[str, str]:
    pid = project_id(name)
    pt = project_title(name)
    se = src_ext(lang)
    he = header_ext(lang)

    if lang == "c":
        header = f"""#pragma once

int {pid}_compute(void);
"""
        core = f"""#include \"core.{he}\"

int {pid}_compute(void) {{
    return 42;
}}
"""
        main = f"""#include <stdio.h>
#include \"core.{he}\"

int main(void) {{
    printf(\"value=%d\\n\", {pid}_compute());
    return 0;
}}
"""
        test = f"""#include <gtest/gtest.h>
extern \"C\" {{
#include \"core.{he}\"
}}

TEST({pt}Exe, CoreValue) {{
    EXPECT_EQ({pid}_compute(), 42);
}}
"""
    else:
        header = """#pragma once

int compute();
"""
        core = """#include \"core.hpp\"

int compute() {
    return 42;
}
"""
        main = """#include <iostream>
#include \"core.hpp\"

int main() {
    std::cout << "value=" << compute() << std::endl;
    return 0;
}
"""
        test = f"""#include <gtest/gtest.h>
#include \"core.{he}\"

TEST({pt}Exe, CoreValue) {{
    EXPECT_EQ(compute(), 42);
}}
"""

    cmake = f"""cmake_minimum_required(VERSION 3.20)

project({pt}
  VERSION 0.1.0
  DESCRIPTION \"{pt} executable model\"
  LANGUAGES {cmake_languages(lang)}
)

{standard_block(lang)}

include(CTest)

add_library(${{PROJECT_NAME}}_core
  src/core.{se}
)

target_include_directories(${{PROJECT_NAME}}_core
  PUBLIC
    ${{CMAKE_CURRENT_SOURCE_DIR}}/include
)

add_executable(${{PROJECT_NAME}}
  src/main.{se}
)
target_link_libraries(${{PROJECT_NAME}} PRIVATE ${{PROJECT_NAME}}_core)

if(BUILD_TESTING)
  add_subdirectory(tests)
endif()
"""

    tests_cmake = f"""{gtest_fetchcontent_block()}

add_executable(${{PROJECT_NAME}}_tests
  test_core.cpp
)

target_link_libraries(${{PROJECT_NAME}}_tests
  PRIVATE
    ${{PROJECT_NAME}}_core
    GTest::gtest_main
)

gtest_discover_tests(${{PROJECT_NAME}}_tests)
"""

    return {
        "CMakeLists.txt": cmake.strip(),
        f"include/core.{he}": header.strip(),
        f"src/core.{se}": core.strip(),
        f"src/main.{se}": main.strip(),
        "tests/CMakeLists.txt": tests_cmake.strip(),
        "tests/test_core.cpp": test.strip(),
    }


def engine_app_model(name: str, lang: str, linkage: str) -> dict[str, str]:
    pid = project_id(name)
    pt = project_title(name)
    se = src_ext(lang)
    he = header_ext(lang)
    default_shared = "ON" if linkage == "shared" else "OFF"

    if lang == "c":
        header = """#pragma once

const char* engine_get_message(void);
"""
        source = """#include \"engine_api.h\"

const char* engine_get_message(void) {
    return "engine-online";
}
"""
        app = """#include <stdio.h>
#include \"engine_api.h\"

int main(void) {
    printf("%s\\n", engine_get_message());
    return 0;
}
"""
        test = f"""#include <gtest/gtest.h>
extern \"C\" {{
#include \"engine_api.{he}\"
}}

TEST({pt}Engine, Message) {{
    EXPECT_STREQ(engine_get_message(), \"engine-online\");
}}
"""
    else:
        header = """#pragma once

namespace engine {
const char* get_message();
}
"""
        source = """#include \"engine_api.hpp\"

namespace engine {
const char* get_message() {
    return "engine-online";
}
} // namespace engine
"""
        app = """#include <iostream>
#include \"engine_api.hpp\"

int main() {
    std::cout << engine::get_message() << std::endl;
    return 0;
}
"""
        test = f"""#include <gtest/gtest.h>
#include \"engine_api.{he}\"

TEST({pt}Engine, Message) {{
    EXPECT_STREQ(engine::get_message(), \"engine-online\");
}}
"""

    cmake = f"""cmake_minimum_required(VERSION 3.20)

project({pt}
  VERSION 0.1.0
  DESCRIPTION \"{pt} engine + app model\"
  LANGUAGES {cmake_languages(lang)}
)

{standard_block(lang)}

include(CTest)

option(ENGINE_SHARED "Build engine library as shared" {default_shared})
set(ENGINE_LIBRARY_TYPE STATIC)
if(ENGINE_SHARED)
  set(ENGINE_LIBRARY_TYPE SHARED)
endif()

add_library(${{PROJECT_NAME}}_engine ${{ENGINE_LIBRARY_TYPE}}
  src/engine_api.{se}
)

target_include_directories(${{PROJECT_NAME}}_engine
  PUBLIC
    ${{CMAKE_CURRENT_SOURCE_DIR}}/include
)

add_executable(${{PROJECT_NAME}}_app
  apps/main.{se}
)
target_link_libraries(${{PROJECT_NAME}}_app PRIVATE ${{PROJECT_NAME}}_engine)

if(BUILD_TESTING)
  add_subdirectory(tests)
endif()
"""

    tests_cmake = f"""{gtest_fetchcontent_block()}

add_executable(${{PROJECT_NAME}}_tests
  test_engine.cpp
)

target_link_libraries(${{PROJECT_NAME}}_tests
  PRIVATE
    ${{PROJECT_NAME}}_engine
    GTest::gtest_main
)

gtest_discover_tests(${{PROJECT_NAME}}_tests)
"""

    return {
        "CMakeLists.txt": cmake.strip(),
        f"include/engine_api.{he}": header.strip(),
        f"src/engine_api.{se}": source.strip(),
        f"apps/main.{se}": app.strip(),
        "tests/CMakeLists.txt": tests_cmake.strip(),
        "tests/test_engine.cpp": test.strip(),
    }


def workspace_model(name: str, lang: str) -> dict[str, str]:
    pid = project_id(name)
    pt = project_title(name)
    se = src_ext(lang)
    he = header_ext(lang)

    if lang == "c":
        core_h = "#pragma once\n\nint core_value(void);"
        core_c = "#include \"core_api.h\"\n\nint core_value(void) { return 7; }"
        math_h = "#pragma once\n\nint math_add(int a, int b);"
        math_c = "#include \"math_api.h\"\n\nint math_add(int a, int b) { return a + b; }"
        app_main = """#include <stdio.h>
#include \"core_api.h\"
#include \"math_api.h\"

int main(void) {
    printf("value=%d\\n", math_add(core_value(), 5));
    return 0;
}
"""
        test = f"""#include <gtest/gtest.h>
extern \"C\" {{
#include \"core_api.{he}\"
#include \"math_api.{he}\"
}}

TEST({pt}Workspace, UsesLibraries) {{
    EXPECT_EQ(math_add(core_value(), 5), 12);
}}
"""
    else:
        core_h = "#pragma once\n\nint core_value();"
        core_c = "#include \"core_api.hpp\"\n\nint core_value() { return 7; }"
        math_h = "#pragma once\n\nint math_add(int a, int b);"
        math_c = "#include \"math_api.hpp\"\n\nint math_add(int a, int b) { return a + b; }"
        app_main = """#include <iostream>
#include \"core_api.hpp\"
#include \"math_api.hpp\"

int main() {
    std::cout << "value=" << math_add(core_value(), 5) << std::endl;
    return 0;
}
"""
        test = f"""#include <gtest/gtest.h>
#include \"core_api.{he}\"
#include \"math_api.{he}\"

TEST({pt}Workspace, UsesLibraries) {{
    EXPECT_EQ(math_add(core_value(), 5), 12);
}}
"""

    top_cmake = f"""cmake_minimum_required(VERSION 3.20)

project({pt}
  VERSION 0.1.0
  DESCRIPTION \"{pt} multi-lib + multi-exe workspace model\"
  LANGUAGES {cmake_languages(lang)}
)

{standard_block(lang)}

include(CTest)

add_subdirectory(libs/core)
add_subdirectory(libs/math)
add_subdirectory(apps/cli)

if(BUILD_TESTING)
  add_subdirectory(tests)
endif()
"""

    core_cmake = f"""add_library(${{PROJECT_NAME}}_core
  src/core_api.{se}
)

target_include_directories(${{PROJECT_NAME}}_core
  PUBLIC
    ${{CMAKE_CURRENT_SOURCE_DIR}}/include
)
"""

    math_cmake = f"""add_library(${{PROJECT_NAME}}_math
  src/math_api.{se}
)

target_include_directories(${{PROJECT_NAME}}_math
  PUBLIC
    ${{CMAKE_CURRENT_SOURCE_DIR}}/include
)
"""

    app_cmake = f"""add_executable(${{PROJECT_NAME}}_cli
  src/main.{se}
)

target_include_directories(${{PROJECT_NAME}}_cli
  PRIVATE
    ${{CMAKE_SOURCE_DIR}}/libs/core/include
    ${{CMAKE_SOURCE_DIR}}/libs/math/include
)

target_link_libraries(${{PROJECT_NAME}}_cli
  PRIVATE
    ${{PROJECT_NAME}}_core
    ${{PROJECT_NAME}}_math
)
"""

    tests_cmake = f"""{gtest_fetchcontent_block()}

add_executable(${{PROJECT_NAME}}_tests
  test_workspace.cpp
)

target_include_directories(${{PROJECT_NAME}}_tests
  PRIVATE
    ${{CMAKE_SOURCE_DIR}}/libs/core/include
    ${{CMAKE_SOURCE_DIR}}/libs/math/include
)

target_link_libraries(${{PROJECT_NAME}}_tests
  PRIVATE
    ${{PROJECT_NAME}}_core
    ${{PROJECT_NAME}}_math
    GTest::gtest_main
)

gtest_discover_tests(${{PROJECT_NAME}}_tests)
"""

    return {
        "CMakeLists.txt": top_cmake.strip(),
        "libs/core/CMakeLists.txt": core_cmake.strip(),
        f"libs/core/include/core_api.{he}": core_h.strip(),
        f"libs/core/src/core_api.{se}": core_c.strip(),
        "libs/math/CMakeLists.txt": math_cmake.strip(),
        f"libs/math/include/math_api.{he}": math_h.strip(),
        f"libs/math/src/math_api.{se}": math_c.strip(),
        "apps/cli/CMakeLists.txt": app_cmake.strip(),
        f"apps/cli/src/main.{se}": app_main.strip(),
        "tests/CMakeLists.txt": tests_cmake.strip(),
        "tests/test_workspace.cpp": test.strip(),
    }


def plugin_shared_model(name: str, lang: str) -> dict[str, str]:
    pid = project_id(name)
    pt = project_title(name)
    se = src_ext(lang)
    he = header_ext(lang)
    api_macro = f"{pid.upper()}_PLUGIN_API"
    export_macro = f"{pid.upper()}_PLUGIN_EXPORTS"

    if lang == "c":
        header = f"""#pragma once

#if defined(_WIN32)
  #if defined({export_macro})
    #define {api_macro} __declspec(dllexport)
  #else
    #define {api_macro} __declspec(dllimport)
  #endif
#else
  #define {api_macro}
#endif

{api_macro} const char* {pid}_plugin_message(void);
"""
        source = f"""#include \"plugin_api.{he}\"

const char* {pid}_plugin_message(void) {{
    return \"plugin-shared-online\";
}}
"""
        app = f"""#include <stdio.h>
#include \"plugin_api.{he}\"

int main(void) {{
    printf(\"%s\\n\", {pid}_plugin_message());
    return 0;
}}
"""
        test = f"""#include <gtest/gtest.h>
extern \"C\" {{
#include \"plugin_api.{he}\"
}}

TEST({pt}PluginShared, Message) {{
    EXPECT_STREQ({pid}_plugin_message(), \"plugin-shared-online\");
}}
"""
    else:
        header = f"""#pragma once

#if defined(_WIN32)
  #if defined({export_macro})
    #define {api_macro} __declspec(dllexport)
  #else
    #define {api_macro} __declspec(dllimport)
  #endif
#else
  #define {api_macro}
#endif

namespace {pid} {{
{api_macro} const char* plugin_message();
}}
"""
        source = f"""#include \"plugin_api.{he}\"

namespace {pid} {{
const char* plugin_message() {{
    return \"plugin-shared-online\";
}}
}} // namespace {pid}
"""
        app = f"""#include <iostream>
#include \"plugin_api.{he}\"

int main() {{
    std::cout << {pid}::plugin_message() << std::endl;
    return 0;
}}
"""
        test = f"""#include <gtest/gtest.h>
#include \"plugin_api.{he}\"

TEST({pt}PluginShared, Message) {{
    EXPECT_STREQ({pid}::plugin_message(), \"plugin-shared-online\");
}}
"""

    cmake = f"""cmake_minimum_required(VERSION 3.20)

project({pt}
  VERSION 0.1.0
  DESCRIPTION \"{pt} shared plugin model\"
  LANGUAGES {cmake_languages(lang)}
)

{standard_block(lang)}

include(CTest)

add_library(${{PROJECT_NAME}}_plugin SHARED
  src/plugin_api.{se}
)

target_include_directories(${{PROJECT_NAME}}_plugin
  PUBLIC
    ${{CMAKE_CURRENT_SOURCE_DIR}}/include
)

target_compile_definitions(${{PROJECT_NAME}}_plugin PRIVATE {export_macro})

add_executable(${{PROJECT_NAME}}_app
  apps/main.{se}
)
target_link_libraries(${{PROJECT_NAME}}_app PRIVATE ${{PROJECT_NAME}}_plugin)

if(BUILD_TESTING)
  add_subdirectory(tests)
endif()
"""

    tests_cmake = f"""{gtest_fetchcontent_block()}

add_executable(${{PROJECT_NAME}}_tests
  test_plugin_shared.cpp
)

target_link_libraries(${{PROJECT_NAME}}_tests
  PRIVATE
    ${{PROJECT_NAME}}_plugin
    GTest::gtest_main
)

gtest_discover_tests(${{PROJECT_NAME}}_tests)
"""

    return {
        "CMakeLists.txt": cmake.strip(),
        f"include/plugin_api.{he}": header.strip(),
        f"src/plugin_api.{se}": source.strip(),
        f"apps/main.{se}": app.strip(),
        "tests/CMakeLists.txt": tests_cmake.strip(),
        "tests/test_plugin_shared.cpp": test.strip(),
    }


def plugin_addon_model(name: str, lang: str, plugin_prefix: str, plugin_suffix: str) -> dict[str, str]:
    pid = project_id(name)
    pt = project_title(name)
    se = src_ext(lang)
    he = header_ext(lang)

    header = """#pragma once

#if defined(__cplusplus)
extern "C" {
#endif

typedef struct addon_context {
    int value;
} addon_context;

int addon_get_api_version(void);
const char* addon_get_name(void);
void* addon_create(void);
void addon_destroy(void* state);
int addon_execute(void* state, const addon_context* ctx);

#if defined(__cplusplus)
} // extern "C"
#endif
"""

    addon_source = """#include "addon_api.__HEADER_EXT__"

#include <stdlib.h>

typedef struct addon_state {
    int accum;
} addon_state;

int addon_get_api_version(void) {
    return 1;
}

const char* addon_get_name(void) {
    return "runtime-addon";
}

void* addon_create(void) {
    addon_state* state = (addon_state*)malloc(sizeof(addon_state));
    if (state != NULL) {
        state->accum = 0;
    }
    return state;
}

void addon_destroy(void* state) {
    free(state);
}

int addon_execute(void* state, const addon_context* ctx) {
    addon_state* s = (addon_state*)state;
    if (s == NULL || ctx == NULL) {
        return -1;
    }
    s->accum += ctx->value;
    return s->accum;
}
""".replace("__HEADER_EXT__", he)

    if lang == "c":
        host = """#include <stdio.h>
#include <stdlib.h>

#if defined(_WIN32)
  #include <windows.h>
#else
  #include <dlfcn.h>
#endif

#include "addon_api.h"

int main(int argc, char** argv) {
    if (argc < 2) {
        fprintf(stderr, "usage: %s <addon-path>\\n", argv[0]);
        return 1;
    }

#if defined(_WIN32)
    HMODULE lib = LoadLibraryA(argv[1]);
    if (!lib) {
        fprintf(stderr, "failed to load addon: %s\\n", argv[1]);
        return 2;
    }
    int (*get_version)(void) = (int (*)(void))GetProcAddress(lib, "addon_get_api_version");
    void* (*create_fn)(void) = (void* (*)(void))GetProcAddress(lib, "addon_create");
    int (*execute_fn)(void*, const addon_context*) = (int (*)(void*, const addon_context*))GetProcAddress(lib, "addon_execute");
    void (*destroy_fn)(void*) = (void (*)(void*))GetProcAddress(lib, "addon_destroy");
#else
    void* lib = dlopen(argv[1], RTLD_NOW);
    if (!lib) {
        fprintf(stderr, "failed to load addon: %s\\n", argv[1]);
        return 2;
    }
    int (*get_version)(void) = (int (*)(void))dlsym(lib, "addon_get_api_version");
    void* (*create_fn)(void) = (void* (*)(void))dlsym(lib, "addon_create");
    int (*execute_fn)(void*, const addon_context*) = (int (*)(void*, const addon_context*))dlsym(lib, "addon_execute");
    void (*destroy_fn)(void*) = (void (*)(void*))dlsym(lib, "addon_destroy");
#endif

    if (!get_version || !create_fn || !execute_fn || !destroy_fn) {
        fprintf(stderr, "addon missing required symbols\\n");
        return 3;
    }

    addon_context ctx = { .value = 5 };
    void* state = create_fn();
    int result = execute_fn(state, &ctx);
    destroy_fn(state);

    printf("addon-api=%d result=%d\\n", get_version(), result);

#if defined(_WIN32)
    FreeLibrary(lib);
#else
    dlclose(lib);
#endif

    return 0;
}
"""
    else:
        host = """#include <iostream>
#include <string>

#if defined(_WIN32)
  #include <windows.h>
#else
  #include <dlfcn.h>
#endif

#include "addon_api.hpp"

int main(int argc, char** argv) {
    if (argc < 2) {
        std::cerr << "usage: " << argv[0] << " <addon-path>" << std::endl;
        return 1;
    }

#if defined(_WIN32)
    HMODULE lib = LoadLibraryA(argv[1]);
    if (!lib) {
        std::cerr << "failed to load addon: " << argv[1] << std::endl;
        return 2;
    }
    auto get_version = reinterpret_cast<int (*)()>(GetProcAddress(lib, "addon_get_api_version"));
    auto create_fn = reinterpret_cast<void* (*)()>(GetProcAddress(lib, "addon_create"));
    auto execute_fn = reinterpret_cast<int (*)(void*, const addon_context*)>(GetProcAddress(lib, "addon_execute"));
    auto destroy_fn = reinterpret_cast<void (*)(void*)>(GetProcAddress(lib, "addon_destroy"));
#else
    void* lib = dlopen(argv[1], RTLD_NOW);
    if (!lib) {
        std::cerr << "failed to load addon: " << argv[1] << std::endl;
        return 2;
    }
    auto get_version = reinterpret_cast<int (*)()>(dlsym(lib, "addon_get_api_version"));
    auto create_fn = reinterpret_cast<void* (*)()>(dlsym(lib, "addon_create"));
    auto execute_fn = reinterpret_cast<int (*)(void*, const addon_context*)>(dlsym(lib, "addon_execute"));
    auto destroy_fn = reinterpret_cast<void (*)(void*)>(dlsym(lib, "addon_destroy"));
#endif

    if (!get_version || !create_fn || !execute_fn || !destroy_fn) {
        std::cerr << "addon missing required symbols" << std::endl;
        return 3;
    }

    addon_context ctx{5};
    void* state = create_fn();
    int result = execute_fn(state, &ctx);
    destroy_fn(state);

    std::cout << "addon-api=" << get_version() << " result=" << result << std::endl;

#if defined(_WIN32)
    FreeLibrary(lib);
#else
    dlclose(lib);
#endif

    return 0;
}
"""

    test = f"""#include <gtest/gtest.h>
extern \"C\" {{
#include \"addon_api.{he}\"
}}

TEST({pt}Addon, ApiSmoke) {{
    EXPECT_EQ(addon_get_api_version(), 1);
    addon_context ctx{{3}};
    void* state = addon_create();
    ASSERT_NE(state, nullptr);
    EXPECT_EQ(addon_execute(state, &ctx), 3);
    addon_destroy(state);
}}
"""

    cmake = f"""cmake_minimum_required(VERSION 3.20)

project({pt}
  VERSION 0.1.0
  DESCRIPTION \"{pt} runtime addon model\"
  LANGUAGES {cmake_languages(lang)}
)

{standard_block(lang)}

include(CTest)

set(ADDON_PREFIX \"{plugin_prefix}\" CACHE STRING \"Runtime addon output prefix\")
set(ADDON_SUFFIX \"{plugin_suffix}\" CACHE STRING \"Runtime addon output suffix\")

add_library(${{PROJECT_NAME}}_addon SHARED
  src/addon_api.{se}
)

target_include_directories(${{PROJECT_NAME}}_addon
  PUBLIC
    ${{CMAKE_CURRENT_SOURCE_DIR}}/include
)

set_target_properties(${{PROJECT_NAME}}_addon PROPERTIES
  PREFIX ""
  OUTPUT_NAME "${{ADDON_PREFIX}}${{PROJECT_NAME}}${{ADDON_SUFFIX}}"
)

add_executable(${{PROJECT_NAME}}_host
  apps/addon_host.{se}
)

target_include_directories(${{PROJECT_NAME}}_host
  PRIVATE
    ${{CMAKE_CURRENT_SOURCE_DIR}}/include
)

if(UNIX AND NOT APPLE)
  target_link_libraries(${{PROJECT_NAME}}_host PRIVATE dl)
endif()

if(BUILD_TESTING)
  add_subdirectory(tests)
  add_test(NAME addon_host_smoke COMMAND ${{PROJECT_NAME}}_host $<TARGET_FILE:${{PROJECT_NAME}}_addon>)
endif()
"""

    tests_cmake = f"""{gtest_fetchcontent_block()}

add_executable(${{PROJECT_NAME}}_tests
  test_addon_api.cpp
)

target_include_directories(${{PROJECT_NAME}}_tests
  PRIVATE
    ${{CMAKE_CURRENT_SOURCE_DIR}}/../include
)

target_link_libraries(${{PROJECT_NAME}}_tests
  PRIVATE
    ${{PROJECT_NAME}}_addon
    GTest::gtest_main
)

gtest_discover_tests(${{PROJECT_NAME}}_tests)
"""

    return {
        "CMakeLists.txt": cmake.strip(),
        f"include/addon_api.{he}": header.strip(),
        f"src/addon_api.{se}": addon_source.strip(),
        f"apps/addon_host.{se}": host.strip(),
        "tests/CMakeLists.txt": tests_cmake.strip(),
        "tests/test_addon_api.cpp": test.strip(),
    }


MODEL_BUILDERS = {
    "lib": lambda a: lib_model(a.project_name, a.lang),
    "exe": lambda a: exe_model(a.project_name, a.lang),
    "engine-app": lambda a: engine_app_model(a.project_name, a.lang, a.engine_linkage),
    "workspace": lambda a: workspace_model(a.project_name, a.lang),
    "plugin-shared": lambda a: plugin_shared_model(a.project_name, a.lang),
    "plugin-addon": lambda a: plugin_addon_model(a.project_name, a.lang, a.plugin_prefix, a.plugin_suffix),
}


def copy_common_artifacts(repo_root: Path, out_dir: Path, with_doctrine: bool) -> None:
    common_root = repo_root / "templates" / "common"

    copy_file(common_root / "tools" / "setup" / "bootstrap.sh", out_dir / "tools" / "setup" / "bootstrap.sh")
    copy_file(common_root / "tools" / "setup" / "bootstrap.ps1", out_dir / "tools" / "setup" / "bootstrap.ps1")
    copy_file(common_root / "tools" / "setup" / "bootstrap.cmd", out_dir / "tools" / "setup" / "bootstrap.cmd")
    os.chmod(out_dir / "tools" / "setup" / "bootstrap.sh", 0o755)

    if with_doctrine:
        copy_file(common_root / "AGENTS.md", out_dir / "AGENTS.md")
        copy_file(common_root / "AI_CONTEXT.md", out_dir / "AI_CONTEXT.md")
        copy_tree(common_root / "docs" / "doctrine", out_dir / "docs" / "doctrine")


def run_setup(out_dir: Path, install: bool) -> int:
    if os.name == "nt":
        cmd = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(out_dir / "tools" / "setup" / "bootstrap.ps1"),
            "--install" if install else "--doctor",
            "--non-interactive",
        ]
    else:
        cmd = [
            "bash",
            str(out_dir / "tools" / "setup" / "bootstrap.sh"),
            "--install" if install else "--doctor",
            "--non-interactive",
        ]

    result = subprocess.run(cmd, cwd=out_dir)
    return result.returncode


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scaffold C/C++ CMake family templates.")
    parser.add_argument("--model", choices=MODELS, required=True)
    parser.add_argument("--lang", choices=LANGS, required=True)
    parser.add_argument("--project-name", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--engine-linkage", choices=["shared", "static"], default="shared")
    parser.add_argument("--plugin-prefix", default="addon_")
    parser.add_argument("--plugin-suffix", default="_plugin")
    parser.add_argument("--cmake-preset", choices=["native", "ninja"], default="native")
    parser.add_argument("--without-doctrine", action="store_true")
    parser.add_argument("--force", action="store_true")

    group = parser.add_mutually_exclusive_group()
    group.add_argument("--setup", action="store_true")
    group.add_argument("--setup-install", action="store_true")

    return parser.parse_args()


def validate_project_name(name: str) -> None:
    if not re.match(r"^[A-Za-z][A-Za-z0-9_-]*$", name):
        raise SystemExit("project-name must match: ^[A-Za-z][A-Za-z0-9_-]*$")


def main() -> int:
    args = parse_args()
    validate_project_name(args.project_name)

    repo_root = Path(__file__).resolve().parents[1]
    out_dir = Path(args.output_dir).resolve()

    if out_dir.exists() and any(out_dir.iterdir()):
        if not args.force:
            raise SystemExit(f"output-dir not empty: {out_dir} (use --force)")
        shutil.rmtree(out_dir)

    out_dir.mkdir(parents=True, exist_ok=True)

    for rel, content in common_files(args.project_name, args.model, args.lang, args.cmake_preset).items():
        write_file(out_dir, rel, content)

    copy_common_artifacts(repo_root, out_dir, with_doctrine=(not args.without_doctrine))

    model_files = MODEL_BUILDERS[args.model](args)
    for rel, content in model_files.items():
        write_file(out_dir, rel, content)

    print(f"Scaffolded {args.model} ({args.lang}) at {out_dir}")

    if args.setup or args.setup_install:
        code = run_setup(out_dir, install=args.setup_install)
        if code != 0:
            print(
                "Setup finished with non-zero status. The project was generated successfully; "
                "review setup output and rerun tools/setup/bootstrap.",
                file=sys.stderr,
            )
            return code

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
