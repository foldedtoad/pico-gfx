# ui.py - small app framework on top of the eezui C module
#
#   App      owns the screens, routes EEZ actions to the active screen,
#            and runs each screen's background task while it is shown.
#   Screen   base class: one subclass per EEZ screen (see screens/).
#
# EEZ actions arrive from C through the MicroPython scheduler. They are only
# queued there; the asyncio task `_action_loop` runs the handlers, so
# handlers may be `async def` and may await.

import asyncio
import eezui


class Screen:
    """Base class for one EEZ screen.

    screen_id   eezui.SCREEN_xxx constant (required)
    enter()     called when the screen becomes active
    leave()     called when another screen replaces it
    run()       optional async background task, cancelled on leave
    on_<action> handler for EEZ action "<action>" (sync or async)
    """
    screen_id = None

    def __init__(self, app):
        self.app = app

    def enter(self):
        pass

    def leave(self):
        pass

    async def run(self):
        pass

    # convenience
    def set(self, name, value):
        self.app.set(name, value)


class App:
    def __init__(self):
        self.screens = {}
        self.current = None
        self._run_task = None
        self._vars = {}
        self._queue = []
        self._flag = asyncio.ThreadSafeFlag()
        self.global_actions = {}          # name -> handler, tried after the screen

    # ---- variables -------------------------------------------------------
    def set(self, name, value):
        """Write an EEZ native variable only if it changed (strings for now)."""
        value = str(value)
        if self._vars.get(name) != value:
            self._vars[name] = value
            eezui.set_var(name, value)

    def get(self, name):
        return self._vars.get(name)

    # ---- screens ---------------------------------------------------------
    def add(self, name, screen_cls):
        self.screens[name] = screen_cls(self)

    def goto(self, name):
        new = self.screens[name]
        if new is self.current:
            return
        if self.current is not None:
            if self._run_task is not None:
                self._run_task.cancel()
                self._run_task = None
            self.current.leave()
        self.current = new
        eezui.load_screen(new.screen_id)
        new.enter()
        self._run_task = asyncio.create_task(self._run_guard(new))

    async def _run_guard(self, screen):
        try:
            await screen.run()
        except asyncio.CancelledError:
            pass

    # ---- actions ---------------------------------------------------------
    def _on_action(self, name):
        # Called via mp_sched_schedule: keep it tiny, never block here.
        self._queue.append(name)
        self._flag.set()

    async def _action_loop(self):
        while True:
            await self._flag.wait()
            while self._queue:
                name = self._queue.pop(0)
                await self._dispatch(name)

    async def _dispatch(self, name):
        handler = getattr(self.current, name, None) if self.current else None
        if handler is None:
            handler = self.global_actions.get(name)
        if handler is None:
            print("ui: unhandled action", name)
            return
        result = handler()
        if hasattr(result, "send"):       # coroutine -> await it
            await result

    # ---- lifecycle -------------------------------------------------------
    def start(self, first_screen, initial_vars=None):
        """Call after hw.start() / hw.add_buttons(). Creates the EEZ UI."""
        for k, v in (initial_vars or {}).items():
            self.set(k, v)
        eezui.on_action(self._on_action)
        eezui.init()
        self.goto(first_screen)

    async def run_forever(self, *background):
        """Run the action loop plus any extra background coroutines."""
        tasks = [asyncio.create_task(self._action_loop())]
        tasks += [asyncio.create_task(c) for c in background]
        await asyncio.gather(*tasks)
