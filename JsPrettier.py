# -*- coding: utf-8 -*-

import json
import os
import platform
import sublime
import sublime_plugin

from subprocess import PIPE, Popen

#
# monkey patch `Region` to be iterable:
sublime.Region.totuple = lambda self: (self.a, self.b)
sublime.Region.__iter__ = lambda self: self.totuple().__iter__()

PLUGIN_NAME = 'JsPrettier'
SETTINGS_FILE = PLUGIN_NAME + '.sublime-settings'
JS_FILE = PLUGIN_NAME.lower() + '.js'
PRETTIER_PATH = os.path.join(sublime.packages_path(), os.path.dirname(os.path.realpath(__file__)), JS_FILE)


class JsPrettierCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        syntax = self.get_syntax()
        if not syntax:
            return

        config = self.get_config()

        if not self.has_selection():
            region = sublime.Region(0, self.view.size())
            source = self.view.substr(region)
            transformed = self.prettier(source, config)
            if transformed:
                self.view.replace(edit, region, transformed)
                sublime.set_timeout(lambda: sublime.status_message(PLUGIN_NAME + ': code formatted.'), 0)
            return
        for region in self.view.sel():
            if region.empty():
                continue
            source = self.view.substr(region)
            transformed = self.prettier(source, config)
            if transformed:
                self.view.replace(edit, region, transformed)
                sublime.set_timeout(lambda: sublime.status_message(PLUGIN_NAME + ': code formatted.'), 0)

    def prettier(self, source, config):
        config = json.dumps(config)
        folder = os.path.dirname(self.view.file_name())
        try:
            p = Popen(['node', PRETTIER_PATH, config, folder],
                      stdout=PIPE, stdin=PIPE, stderr=PIPE,
                      env=self.get_env(), shell=self.is_windows())
        except OSError:
            raise Exception(PLUGIN_NAME + ": couldn't find node.js. Make sure it's in your "
                            '$PATH by running `node -v` in your command-line.')
        stdout, stderr = p.communicate(input=source.encode('utf-8'))
        if stdout:
            return stdout.decode('utf-8')
        else:
            sublime.error_message(PLUGIN_NAME + ' error:\n%s' % stderr.decode('utf-8'))

    def get_env(self):
        env = None
        if self.is_osx():
            env = os.environ.copy()
            env['PATH'] += self.get_node_path()
        return env

    def get_node_path(self):
        return self.get_settings().get('node_path')

    def get_settings(self):
        settings = self.view.settings().get(PLUGIN_NAME)
        if settings is None:
            settings = sublime.load_settings(SETTINGS_FILE)
        return settings

    def get_config(self):
        return self.get_settings().get('config')

    @staticmethod
    def get_syntax():
        return 'js'
        # if self.is_js():
        #     return 'js'
        # if self.is_unsaved_buffer_without_syntax():
        #     return 'js'
        # return False

    def has_selection(self):
        for sel in self.view.sel():
            start, end = sel
            if start != end:
                return True
        return False

    @staticmethod
    def is_osx():
        return platform.system() == 'Darwin'

    @staticmethod
    def is_windows():
        return platform.system() == 'Windows'

    def is_unsaved_buffer_without_syntax(self):
        return self.view.file_name() is None and self.is_plaintext() is True

    def is_plaintext(self):
        return self.view.scope_name(0).startswith('text.plain')

    def is_js(self):
        return self.view.scope_name(0).startswith('source.js')