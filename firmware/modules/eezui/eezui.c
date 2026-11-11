// eezui.c - MicroPython <-> EEZ Studio (LVGL C) bridge for pico-gfx
//
// Python API:
//   eezui.init()                      create EEZ screens, load the first one, start ui_tick timer
//   eezui.load_screen(id)             switch screen (eezui.SCREEN_WATCH, ...)
//   eezui.set_rotation(name, tenths)  rotate an image widget (0.1 degree units)
//   eezui.set_pivot(name, x, y)       set an image widget's rotation pivot
//   eezui.set_var(name, value)        write an EEZ native variable   (none defined yet)
//   eezui.get_var(name)               read it back
//   eezui.on_action(callback)         callback(name) for EEZ actions   (none defined yet)
//
// Adding things in EEZ later:
//   native variable -> storage + get_var_xxx/set_var_xxx below + a line in
//                      eezui_set_var / eezui_get_var
//   action          -> an action_xxx() stub calling eezui_dispatch()
//   widget to drive -> a line in widget_by_name()
// The link step fails with "undefined reference to ..." until you do.

#include <string.h>
#include "py/runtime.h"
#include "py/obj.h"

#include "lvgl.h"
#include "ui.h"
#include "screens.h"
#include "vars.h"
#include "actions.h"

// ---------------------------------------------------------------------------
// Native variables (Python writes, EEZ's tick_screen_*() reads) - none yet
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Actions (EEZ event -> Python callback, run via the MicroPython scheduler)
// ---------------------------------------------------------------------------

MP_REGISTER_ROOT_POINTER(mp_obj_t eezui_action_cb);   // keeps callback alive across GC

// Call from each action stub, e.g.
//   void action_on_x(lv_event_t *e) { eezui_dispatch(MP_OBJ_NEW_QSTR(MP_QSTR_on_x)); }
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
// Widgets Python may address by name ("Name" property in EEZ)
// ---------------------------------------------------------------------------

static lv_obj_t *widget_by_name(const char *name) {
    if (strcmp(name, "img_hour") == 0)   return objects.img_hour;
    if (strcmp(name, "img_minute") == 0) return objects.img_minute;
    if (strcmp(name, "img_second") == 0) return objects.img_second;
    return NULL;
}

static lv_obj_t *widget_arg(mp_obj_t name_in) {
    const char *name = mp_obj_str_get_str(name_in);
    lv_obj_t *obj = widget_by_name(name);
    if (obj == NULL) {
        mp_raise_msg_varg(&mp_type_ValueError,
            MP_ERROR_TEXT("unknown widget '%s' (or eezui.init() not called)"), name);
    }
    return obj;
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
    tick_timer = lv_timer_create(tick_cb, 40, NULL);
    initialised = true;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(eezui_init_obj, eezui_init);

static mp_obj_t eezui_set_var(mp_obj_t name_in, mp_obj_t value_in) {
    (void)value_in;
    mp_raise_msg_varg(&mp_type_ValueError, MP_ERROR_TEXT("unknown EEZ variable '%s'"),
        mp_obj_str_get_str(name_in));
}
static MP_DEFINE_CONST_FUN_OBJ_2(eezui_set_var_obj, eezui_set_var);

static mp_obj_t eezui_get_var(mp_obj_t name_in) {
    mp_raise_msg_varg(&mp_type_ValueError, MP_ERROR_TEXT("unknown EEZ variable '%s'"),
        mp_obj_str_get_str(name_in));
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

static mp_obj_t eezui_set_rotation(mp_obj_t name_in, mp_obj_t tenths_in) {
    lv_obj_t *obj = widget_arg(name_in);
    lv_image_set_rotation(obj, (int32_t)mp_obj_get_int(tenths_in));
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(eezui_set_rotation_obj, eezui_set_rotation);

static mp_obj_t eezui_set_pivot(mp_obj_t name_in, mp_obj_t x_in, mp_obj_t y_in) {
    lv_obj_t *obj = widget_arg(name_in);
    lv_image_set_pivot(obj, (int32_t)mp_obj_get_int(x_in), (int32_t)mp_obj_get_int(y_in));
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_3(eezui_set_pivot_obj, eezui_set_pivot);

static const mp_rom_map_elem_t eezui_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__),     MP_ROM_QSTR(MP_QSTR_eezui) },
    { MP_ROM_QSTR(MP_QSTR_init),         MP_ROM_PTR(&eezui_init_obj) },
    { MP_ROM_QSTR(MP_QSTR_set_var),      MP_ROM_PTR(&eezui_set_var_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_var),      MP_ROM_PTR(&eezui_get_var_obj) },
    { MP_ROM_QSTR(MP_QSTR_load_screen),  MP_ROM_PTR(&eezui_load_screen_obj) },
    { MP_ROM_QSTR(MP_QSTR_on_action),    MP_ROM_PTR(&eezui_on_action_obj) },
    { MP_ROM_QSTR(MP_QSTR_set_rotation), MP_ROM_PTR(&eezui_set_rotation_obj) },
    { MP_ROM_QSTR(MP_QSTR_set_pivot),    MP_ROM_PTR(&eezui_set_pivot_obj) },
    { MP_ROM_QSTR(MP_QSTR_SCREEN_WATCH), MP_ROM_INT(SCREEN_ID_WATCH) },
};
static MP_DEFINE_CONST_DICT(eezui_globals, eezui_globals_table);

const mp_obj_module_t eezui_user_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&eezui_globals,
};
MP_REGISTER_MODULE(MP_QSTR_eezui, eezui_user_cmodule);
