#ifndef EEZ_LVGL_UI_SCREENS_H
#define EEZ_LVGL_UI_SCREENS_H

#include <lvgl.h>

#ifdef __cplusplus
extern "C" {
#endif

// Screens

enum ScreensEnum {
    _SCREEN_ID_FIRST = 1,
    SCREEN_ID_MAIN = 1,
    SCREEN_ID_WATCH = 2,
    _SCREEN_ID_LAST = 2
};

typedef struct _objects_t {
    lv_obj_t *main;
    lv_obj_t *watch;
    lv_obj_t *lbl_status;
    lv_obj_t *btn_minus;
    lv_obj_t *btn_press;
    lv_obj_t *btn_plus;
    lv_obj_t *img_dial;
    lv_obj_t *img_second;
    lv_obj_t *img_hour;
    lv_obj_t *img_minute;
} objects_t;

extern objects_t objects;

void create_screen_main();
void tick_screen_main();

void create_screen_watch();
void tick_screen_watch();

void tick_screen_by_id(enum ScreensEnum screenId);
void tick_screen(int screen_index);

void create_screens();

#ifdef __cplusplus
}
#endif

#endif /*EEZ_LVGL_UI_SCREENS_H*/