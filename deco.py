#!/usr/bin/env python
# -*- coding: utf-8 -*-

from functools import update_wrapper


def disable(func):
    '''
    Disable a decorator by re-assigning the decorator's name
    to this function. For example, to turn off memoization:

    >>> memo = disable
    '''
    @decorator(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper


def decorator(dec):
    '''
    Decorate a decorator so that it inherits the docstrings
    and stuff from the function it's decorating.
    '''
    def decorated(func):
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        update_wrapper(wrapper, decorated)
        return wrapper
    update_wrapper(decorated, dec)
    return decorated


def countcalls(func):
    '''Decorator that counts calls made to the function decorated.'''

    @decorator(func)
    def wrapper(*args):
        wrapper.calls += 1
        return func(*args)
    wrapper.calls = 0
    return wrapper


def memo(func):
    '''
    Memoize a function so that it caches all return values for
    faster future lookups.
    '''
    cache = dict()

    @decorator(func)
    def wrapper(*args):
        try:
            key = tuple(args)
            if key not in cache:
                cache[key] = func(*args)
            return cache[key]
        except TypeError:
            return func(*args)
    return wrapper


def n_ary(func):
    '''
    Given binary function f(x, y), return an n_ary function such
    that f(x, y, z) = f(x, f(y,z)), etc. Also allow f(x) = x.
    '''

    @decorator(func)
    def wrapper(*args):
        if len(args) == 1:
            return args[0]
        if len(args) == 2:
            return func(*args)
        return func(args[0], wrapper(*args[1:]))
    return wrapper


def trace(trace_spacer):
    '''Trace calls made to function decorated.

    @trace("____")
    def fib(n):
        ....

    >>> fib(3)
     --> fib(3)
    ____ --> fib(2)
    ________ --> fib(1)
    ________ <-- fib(1) == 1
    ________ --> fib(0)
    ________ <-- fib(0) == 1
    ____ <-- fib(2) == 2
    ____ --> fib(1)
    ____ <-- fib(1) == 1
     <-- fib(3) == 3

    '''

    def tracer(func):
        func.trace_spacer = ""
        @decorator(func)
        def wrapper(*args):
            arg_str = ', '.join(list(map(str, args)))
            spacer = wrapper.trace_spacer
            print(f"{spacer} --> {func.__name__}({arg_str})")
            spacer = spacer + trace_spacer
            wrapper.trace_spacer = spacer
            res = func(*args)
            spacer = spacer[:-len(trace_spacer)]
            wrapper.trace_spacer = spacer
            print(f"{spacer} <-- {func.__name__}({arg_str}) == {res}")
            return res
        return wrapper
    return tracer



@memo
@countcalls
@n_ary
def foo(a, b):
    return a + b


@countcalls
@memo
@n_ary
def bar(a, b):
    return a * b


@countcalls
@trace("####")
@memo
def fib(n):
    """Some doc"""
    return 1 if n <= 1 else fib(n-1) + fib(n-2)



def main():


    print(foo(4, 3))
    print(foo(4, 3, 2))
    print(foo(4, 3))
    print("foo was called", foo.calls, "times")

    print(bar(4, 3))
    print(bar(4, 3, 2))
    print(bar(4, 3, 2, 1))
    print("bar was called", bar.calls, "times")


    print(fib.__doc__)
    print(fib(3))
    print(fib.calls, 'calls made')


if __name__ == '__main__':
    main()
