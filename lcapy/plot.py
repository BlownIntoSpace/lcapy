"""
This module performs plotting using matplotlib.

Copyright 2014, 2015 Michael Hayes, UCECE
"""

import numpy as np
from matplotlib.pyplot import figure

# Perhaps add Formatter classes that will produce the plot data?


def plot_pole_zero(obj, **kwargs):

    poles = obj.poles()
    zeros = obj.zeros()
    try:
        p = np.array([complex(p.evalf()) for p in poles.keys()])
        z = np.array([complex(z.evalf()) for z in zeros.keys()])
    except TypeError:
        raise TypeError('Cannot plot poles and zeros of symbolic expression')

    fig = figure()
    ax = fig.add_subplot(111)

    ax.axvline(0, color='0.7')
    ax.axhline(0, color='0.7')
    ax.axis('equal')
    ax.grid()

    a = np.hstack((p, z))
    x_min = a.real.min()
    x_max = a.real.max()
    y_min = a.imag.min()
    y_max = a.imag.max()

    x_extra, y_extra = 0.0, 0.0

    # This needs tweaking for better bounds.
    if len(a) >= 2:
        x_extra, y_extra = 0.1 * (x_max - x_min), 0.1 * (y_max - y_min)
    if x_extra == 0:
        x_extra += 1.0
    if y_extra == 0:
        y_extra += 1.0

    ax.set_xlim(x_min - 0.5 * x_extra, x_max + 0.5 * x_extra)
    ax.set_ylim(y_min - 0.5 * y_extra, y_max + 0.5 * y_extra)

    # TODO, annotate with number of times a pole or zero is repeated.
    ax.plot(z.real, z.imag, 'bo', fillstyle='none', ms=10, **kwargs)
    ax.plot(p.real, p.imag, 'bx', fillstyle='none', ms=10, **kwargs)


def plot_frequency(obj, f, **kwargs):

    from matplotlib.pyplot import figure

    # FIXME, determine useful frequency range...
    if f is None:
        f = (-0.2, 2)
    if isinstance(f, (int, float)):
        f = (0, f)
    if isinstance(f, tuple):
        f = np.linspace(f[0], f[1], 400)

    V = obj(f)

    # TODO, handle different formats; real/imag, mag/phase

    fig = figure()
    ax = fig.add_subplot(111)
    ax.plot(f, abs(V), **kwargs)
    ax.set_xlabel(obj.domain_label)
    ax.set_ylabel(obj.label)
    ax.grid(True)


def plot_time(obj, t, **kwargs):

    # FIXME, determine useful time range...
    if t is None:
        t = (-0.2, 2)
    if isinstance(t, (int, float)):
        t = (0, t)
    if isinstance(t, tuple):
        t = np.linspace(t[0], t[1], 400)

    v = obj(t)

    fig = figure()
    ax = fig.add_subplot(111)
    ax.plot(t, v, **kwargs)
    ax.set_xlabel(obj.domain_label)
    ax.set_ylabel(obj.label)
    ax.grid(True)
