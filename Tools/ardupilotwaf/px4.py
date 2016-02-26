#!/usr/bin/env python
# encoding: utf-8

"""
Waf tool for PX4 build
"""

from waflib import Task, Utils
from waflib.TaskGen import after_method, before_method, feature

import os

_dynamic_env_data = {}
def _load_dynamic_env_data(bld):
    bldnode = bld.bldnode.make_node('modules/PX4Firmware')
    for name in ('cxx_flags', 'include_dirs', 'definitions'):
        _dynamic_env_data[name] = bldnode.find_node(name).read().split(';')

    _dynamic_env_data['DEFINES'] = [
        'NUTTX_GIT_VERSION="%s"' % bld.git_submodule_head_hash('PX4NuttX')[:8],
        'PX4_GIT_VERSION="%s"' % bld.git_submodule_head_hash('PX4Firmware')[:8],
    ]

@feature('ap_stlib', 'ap_program')
@before_method('process_source')
def px4_dynamic_env(self):
    # The generated files from configuration possibly don't exist if it's just
    # a list command (TODO: figure out a better way to address that).
    if self.bld.cmd == 'list':
        return

    if not _dynamic_env_data:
        _load_dynamic_env_data(self.bld)

    self.env.append_value('INCLUDES', _dynamic_env_data['include_dirs'])
    self.env.prepend_value('CXXFLAGS', _dynamic_env_data['cxx_flags'])
    self.env.prepend_value('CXXFLAGS', _dynamic_env_data['definitions'])
    self.env.DEFINES += _dynamic_env_data['DEFINES']

# Single static library
# NOTE: This only works only for local static libraries dependencies - fake
# libraries aren't supported yet
@feature('ap_program')
@after_method('apply_link')
@before_method('process_use')
def px4_import_objects_from_use(self):
    queue = Utils.to_list(getattr(self, 'use', []))
    names = set()

    while queue:
        name = queue.pop(0)
        if name in names:
            continue
        names.add(name)

        try:
            tg = self.bld.get_tgen_by_name(name)
        except Errors.WafError:
            continue

        tg.post()
        for t in getattr(tg, 'compiled_tasks', []):
            self.link_task.set_inputs(t.outputs)

        queue.extend(Utils.to_list(getattr(tg, 'use', [])))

class px4_copy_ap_program_lib(Task.Task):
    run_str = '${CP} ${SRC} ${PX4_AP_PROGRAM_LIB}'

    def runnable_status(self):
        status = super(px4_copy_ap_program_lib, self).runnable_status()
        if status != Task.SKIP_ME:
            return status

        pseudo_target = self.get_pseudo_target()
        try:
            if pseudo_target.sig != self.inputs[0].sig:
                status = Task.RUN_ME
        except AttributeError:
            status = Task.RUN_ME

        return status

    def get_pseudo_target(self):
        if hasattr(self, 'pseudo_target'):
            return self.pseudo_target

        bldnode = self.generator.bld.bldnode
        abspath = self.env.PX4_AP_PROGRAM_LIB
        relpath = os.path.relpath(abspath, bldnode.abspath())
        self.pseudo_target = bldnode.make_node(relpath)
        return self.pseudo_target

    def keyword(self):
        return 'PX4: Copying program library'

    def post_run(self):
        super(px4_copy_ap_program_lib, self).post_run()
        pseudo_target = self.get_pseudo_target()
        pseudo_target.sig = pseudo_target.cache_sig = self.inputs[0].sig

@feature('ap_program')
@after_method('process_source')
def px4_firmware(self):
    self.px4_copy_task = self.create_task('px4_copy_ap_program_lib')
    self.px4_copy_task.set_inputs(self.link_task.outputs)

    self.firmware_task = self.create_cmake_build_task('px4', 'firmware_nuttx')
    self.firmware_task.set_run_after(self.px4_copy_task)

def configure(cfg):
    cfg.load('cmake')
    cfg.find_program('cp')

    bldnode = cfg.bldnode.make_node(cfg.variant)
    env = cfg.env

    def srcpath(path):
        return cfg.srcnode.make_node(path).abspath()

    def bldpath(path):
        return bldnode.make_node(path).abspath()

    bldnode.make_node('px4-extra-files').mkdir()

    program_lib_name = cfg.env.cxxstlib_PATTERN % 'ap_program'
    env.PX4_AP_PROGRAM_LIB = bldpath('px4-extra-files/%s' % program_lib_name)

    env.PX4_CMAKE_VARS = dict(
        CONFIG='nuttx_px4fmu-v%s_apm' % env.get_flat('PX4_VERSION'),
        CMAKE_MODULE_PATH=srcpath('Tools/ardupilotwaf/px4/cmake'),
        UAVCAN_LIBUAVCAN_PATH=srcpath('modules/uavcan'),
        NUTTX_SRC=srcpath('modules/PX4NuttX'),
        APM_PROGRAM_LIB=env.PX4_AP_PROGRAM_LIB,
    )

def build(bld):
    version = bld.env.get_flat('PX4_VERSION')
    px4 = bld(
        features='cmake_configure',
        name='px4',
        cmake_src=bld.srcnode.find_dir('modules/PX4Firmware'),
        cmake_vars=bld.env.PX4_CMAKE_VARS,
        group='dynamic_sources',
    )

    px4.cmake_build(
        'msg_gen',
        group='dynamic_sources',
        cmake_output_patterns='src/modules/uORB/topics/*.h',
    )
    px4.cmake_build(
        'prebuild_targets',
        group='dynamic_sources',
        cmake_output_patterns=[
            'px4fmu-v%s/NuttX/nuttx-export/**/*.h' % version,
        ]
    )
