#!/usr/bin/env python
# -*- encoding: utf-8 -*-

from pickle import GLOBAL
import threading
from .apiKey import apiKey

from .model import *
from .paths import *
from .settings import *


VERSION = '2022.10.31.1'

print_mutex = threading.Lock()


class Printf(object):

    @staticmethod
    def err():
        global print_mutex
        print_mutex.acquire()
        print("error")
        print_mutex.release()
        

    @staticmethod
    def success():
        global print_mutex
        print_mutex.acquire()
        print("success")
        print_mutex.release()


