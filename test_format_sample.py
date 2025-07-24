import os
import sys
import time


def badly_formatted_function(x, y):
    if x > y:
        return x + y
    else:
        return x - y


class BadlyFormattedClass:
    def __init__(self, arg1, arg2, arg3):
        self.arg1 = arg1
        self.arg2 = arg2
        self.arg3 = arg3


if __name__ == "__main__":
    print("hello world")
