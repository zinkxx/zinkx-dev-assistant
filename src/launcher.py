import multiprocessing
import sys
import os


def run_menubar():
    from app import ZinkxDevAssistant

    app = ZinkxDevAssistant()
    app.run()


def run_window():
    from main_window import run_main_window

    run_main_window()


if __name__ == "__main__":
    multiprocessing.set_start_method("spawn", force=True)

    # Main window ayrı process
    p = multiprocessing.Process(target=run_window)
    p.start()

    # Menü bar MAIN THREAD / MAIN PROCESS
    run_menubar()
