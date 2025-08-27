import pybind11
from setuptools import setup, Extension

ext_modules = [
    Extension(
        'reward_tracker',
        ['reward_tracker.cpp'],
        include_dirs=[pybind11.get_include()],
        language='c++',
        extra_compile_args=['-O3', '-Wall', '-shared', '-std=c++11', '-fPIC'],
    ),
]

setup(
    name='reward_tracker',
    ext_modules=ext_modules,
)
