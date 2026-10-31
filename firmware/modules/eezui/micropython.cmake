# eezui - bridges EEZ Studio's generated LVGL C code to MicroPython.
# Pulled into the lvgl_micropython build via the EEZUI_MODULE environment
# variable (see tools/build_fw.sh).

add_library(usermod_eezui INTERFACE)

# Everything EEZ Studio generates. GLOB runs at configure time; the binding's
# make.py does a clean build every time, so new EEZ files are always picked up.
file(GLOB EEZUI_GENERATED_SRC ${CMAKE_CURRENT_LIST_DIR}/ui/*.c)

target_sources(usermod_eezui INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/eezui.c
    ${EEZUI_GENERATED_SRC}
)

# lvgl.h / lv_conf.h come from usermod_lvgl's interface include dirs.
target_include_directories(usermod_eezui INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
    ${CMAKE_CURRENT_LIST_DIR}/ui
)

target_link_libraries(usermod INTERFACE usermod_eezui)
