from __future__ import print_function


def run_until(loop, cond_func, timeout=5.0):
    '''
    Registers a periodic callback that stops the loop when cond_func() == True
    '''
    if cond_func() or timeout <= 0.0:
        loop.stop()
        return

    timeout -= 0.1
    loop.call_later(0.1, run_until, loop, cond_func, timeout)
