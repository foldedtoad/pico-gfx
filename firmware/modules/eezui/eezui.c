// eezui.c - MicroPython <-> EEZ Studio (LVGL C) bridge for pico-gfx
//
// Python API:
//   eezui.init()                      create EEZ screens, load main, start ui_tick timer
//   eezui.set_var(name, value)        write an EEZ native variable
//   eezui.get_var(name)               read it back
//   eezui.load_screen(id)             switch screen (eezui.SCREEN_MAIN, ...)
//   eezui.on_action(callback)         callback(name) for EEZ actions (none defined yet)
//
// When you add a native variable in EEZ: add its storage + get/set below,
// and a line in eezui_set_var / eezui_get_var. The link step fails with
// "undefined reference to get_var_xxx" until you do - that is your checklist.

#include <string.h>
#include "py/runtime.h"
#include "py/obj.h"

#include "lvgl.h"
#include "ui.h"
#include "screens.h"
#include "vars.h"
#include "actions.h"

// ---------------------------------------------------------------------------
// Native variables (Python writes, EEZ's tick_screen_*() reads)
// ---------------------------------------------------------------------------

static char v_status_text[64] = "";

const char *get_var_status_text(void) {
    return v_status_text;
}

void set_var_status_text(const char *value) {
    strncpy(v_status_text, value ? value : "", sizeof(v_status_text) - 1);
    v_status_text[sizeof(v_status_text) - 1] = '\0';
}

// ---------------------------------------------------------------------------
// Actions (EEZ event -> Python callback, run via the MicroPython scheduler)
// ---------------------------------------------------------------------------

MP_REGISTER_ROOT_POINTER(mp_obj_t eezui_action_cb);   // keeps callback alive across GC

// Call from each generated action stub, e.g.
//   void action_on_start(lv_event_t *e) { eezui_dispatch(MP_OBJ_NEW_QSTR(MP_QSTR_on_start)); }
void eezui_dispatch(mp_obj_t name) {
    mp_obj_t cb = MP_STATE_VM(eezui_action_cb);
    if (cb != MP_OBJ_NULL && cb != mp_const_none) {
        mp_sched_schedule(cb, name);
    }
}

// ---------------------------------------------------------------------------
// ui_tick() driven by an LVGL timer, so Python never has to call it
// ---------------------------------------------------------------------------

static lv_timer_t *tick_timer = NULL;
static bool initialised = false;

static void tick_cb(lv_timer_t *t) {
    (void)t;
    ui_tick();
}

// ---------------------------------------------------------------------------
// Python API
// ---------------------------------------------------------------------------

static mp_obj_t eezui_init(void) {
    if (initialised) {
        // Static C state survives a soft reboot, LVGL's heap does not.
        mp_raise_msg(&mp_type_RuntimeError,
            MP_ERROR_TEXT("eezui already initialised; hard reset (machine.reset()) required"));
    }
    if (!lv_is_initialized()) {
        mp_raise_msg(&mp_type_RuntimeError,
            MP_ERROR_TEXT("LVGL not initialised; create the display first"));
    }
    ui_init();
    tick_timer = lv_timer_create(tick_cb, 40, NULL);   // ~25 Hz variable -> widget sync
    initialised = true;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(eezui_init_obj, eezui_init);

static mp_obj_t eezui_set_var(mp_obj_t name_in, mp_obj_t value_in) {
    const char *name = mp_obj_str_get_str(name_in);

    if (strcmp(name, "status_text") == 0) {
        set_var_status_text(mp_obj_str_get_str(value_in));
    } else {
        mp_raise_msg_varg(&mp_type_ValueError, MP_ERROR_TEXT("unknown EEZ variable '%s'"), name);
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(eezui_set_var_obj, eezui_set_var);

static mp_obj_t eezui_get_var(mp_obj_t name_in) {
    const char *name = mp_obj_str_get_str(name_in);

    if (strcmp(name, "status_text") == 0) {
        const char *s = get_var_status_text();
        return mp_obj_new_str(s, strlen(s));
    }
    mp_raise_msg_varg(&mp_type_ValueError, MP_ERROR_TEXT("unknown EEZ variable '%s'"), name);
}
static MP_DEFINE_CONST_FUN_OBJ_1(eezui_get_var_obj, eezui_get_var);

static mp_obj_t eezui_load_screen(mp_obj_t id_in) {
    mp_int_t id = mp_obj_get_int(id_in);
    if (id < _SCREEN_ID_FIRST || id > _SCREEN_ID_LAST) {
        mp_raise_ValueError(MP_ERROR_TEXT("bad screen id"));
    }
    loadScreen((enum ScreensEnum)id);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(eezui_load_screen_obj, eezui_load_screen);

static mp_obj_t eezui_on_action(mp_obj_t cb) {
    if (cb != mp_const_none && !mp_obj_is_callable(cb)) {
        mp_raise_TypeError(MP_ERROR_TEXT("callback must be callable or None"));
    }
    MP_STATE_VM(eezui_action_cb) = cb;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(eezui_on_action_obj, eezui_on_action);

static const mp_rom_map_elem_t eezui_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__),    MP_ROM_QSTR(MP_QSTR_eezui) },
    { MP_ROM_QSTR(MP_QSTR_init),        MP_ROM_PTR(&eezui_init_obj) },
    { MP_ROM_QSTR(MP_QSTR_set_var),     MP_ROM_PTR(&eezui_set_var_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_var),     MP_ROM_PTR(&eezui_get_var_obj) },
    { MP_ROM_QSTR(MP_QSTR_load_screen), MP_ROM_PTR(&eezui_load_screen_obj) },
    { MP_ROM_QSTR(MP_QSTR_on_action),   MP_ROM_PTR(&eezui_on_action_obj) },
    { MP_ROM_QSTR(MP_QSTR_SCREEN_MAIN), MP_ROM_INT(SCREEN_ID_MAIN) },
};
static MP_DEFINE_CONST_DICT(eezui_globals, eezui_globals_table);

const mp_obj_module_t eezui_user_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&eezui_globals,
};
MP_REGISTER_MODULE(MP_QSTR_eezui, eezui_user_cmodule);
