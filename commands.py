# This is a sample commands.py.  You can add your own commands here.
#
# Please refer to commands_full.py for all the default commands and a complete
# documentation.  Do NOT add them all here, or you may end up with defunct
# commands when upgrading ranger.

# A simple command for demonstration purposes follows.
# -----------------------------------------------------------------------------

from __future__ import (absolute_import, division, print_function)

# You can import any python module as needed.
import os

# You always need to import ranger.api.commands here to get the Command class:
from ranger.api.commands import Command

#Navigate
import time
import subprocess

from ranger.api.commands import Command
from ranger.ext.get_executables import get_executables

# Any class that is a subclass of "Command" will be integrated into ranger as a
# command.  Try typing ":my_edit<ENTER>" in ranger!
class my_edit(Command):
    # The so-called doc-string of the class will be visible in the built-in
    # help that is accessible by typing "?c" inside ranger.
    """:my_edit <filename>

    A sample command for demonstration purposes that opens a file in an editor.
    """

    # The execute method is called when you run this command in ranger.
    def execute(self):
        # self.arg(1) is the first (space-separated) argument to the function.
        # This way you can write ":my_edit somefilename<ENTER>".
        if self.arg(1):
            # self.rest(1) contains self.arg(1) and everything that follows
            target_filename = self.rest(1)
        else:
            # self.fm is a ranger.core.filemanager.FileManager object and gives
            # you access to internals of ranger.
            # self.fm.thisfile is a ranger.container.file.File object and is a
            # reference to the currently selected file.
            target_filename = self.fm.thisfile.path

        # This is a generic function to print text in ranger.
        self.fm.notify("Let's edit the file " + target_filename + "!")

        # Using bad=True in fm.notify allows you to print error messages:
        if not os.path.exists(target_filename):
            self.fm.notify("The given file does not exist!", bad=True)
            return

        # This executes a function from ranger.core.acitons, a module with a
        # variety of subroutines that can help you construct commands.
        # Check out the source, or run "pydoc ranger.core.actions" for a list.
        self.fm.edit_file(target_filename)

    # The tab method is called when you press tab, and should return a list of
    # suggestions that the user will tab through.
    # tabnum is 1 for <TAB> and -1 for <S-TAB> by default
    def tab(self, tabnum):
        # This is a generic tab-completion function that iterates through the
        # content of the current directory.
        return self._tab_directory_content()








class fzf_select(Command):
    """
    :fzf_select
    Find a file using fzf and rg with enhanced preview and styling.
    With a prefix argument to select only directories.
    """
    def execute(self):
        hidden = '--hidden' if self.fm.settings.show_hidden else ''
        only_directories = '--type d' if self.quantifier else ''
        
        rg_command = f"rg --files {hidden} {only_directories} " \
                     f"--glob '!.git' --glob '!*.py[co]' --glob '!__pycache__' " \
                     f"--glob '!node_modules' --glob '!.vscode' --glob '!.Trash' " \
                     f"--no-messages --no-ignore-vcs"

        preview_command = '''
            bat --style=numbers,changes,header --color=always --theme=Nord --line-range :100 {}
        '''

        fzf_command = f'fzf --ansi '\
                      f'--preview "{preview_command}" '\
                      f'--preview-window=right:50% '\
                      f'--bind "ctrl-/:toggle-preview" '\
                      f'--header "Search Files in CD/ " '\
                      f'--border=sharp --margin=1 --info=inline-right --no-scrollbar '\
                      f'--prompt "" '

        try:
            process = subprocess.Popen(
                f'{rg_command} | {fzf_command}',
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True,
                text=True
            )
            stdout, stderr = process.communicate()

            if process.returncode == 0 and stdout:
                selected = os.path.abspath(stdout.strip())
                if os.path.isdir(selected):
                    self.fm.cd(selected)
                else:
                    self.fm.select_file(selected)
            elif process.returncode != 130:  # 130 is the exit code when fzf is cancelled
                self.fm.notify('fzf_select failed', bad=True)
        except Exception as e:
            self.fm.notify(f'Error in fzf_select: {str(e)}', bad=True)


class fzf_locate(Command):
    """
    :fzf_locate
    Find a file using rg and fzf.
    With a prefix argument select only directories.
    See: https://github.com/BurntSushi/ripgrep and https://github.com/junegunn/fzf
    """
    def execute(self):
        import subprocess
        
        exclude_dirs = ['.git', 'node_modules', '.trash','.Trash']
        exclude_args = ' '.join([f"--glob '!{d}'" for d in exclude_dirs])
        
        if self.quantifier:
            # Select only directories
            command = f"rg --hidden --files --null {exclude_args} $HOME | xargs -0 dirname | uniq | fzf -e -i --algo=v1"
        else:
            # Select files and directories
            command = f"rg --hidden --files --null {exclude_args} $HOME | fzf -e -i --algo=v1 --read0"
        
        fzf = self.fm.execute_command(command, stdout=subprocess.PIPE)
        stdout, stderr = fzf.communicate()
        if fzf.returncode == 0:
            fzf_file = os.path.abspath(stdout.decode('utf-8').rstrip('\n'))
            if os.path.isdir(fzf_file):
                self.fm.cd(fzf_file)
            else:
                self.fm.select_file(fzf_file)



        def show_error_in_console(msg, fm):
            fm.notify(msg, bad=True)

        def navigate_path(fm, selected):
            if not selected:
                return

            selected = os.path.abspath(selected)
            if os.path.isdir(selected):
                fm.cd(selected)
            elif os.path.isfile(selected):
                fm.select_file(selected)
            else:
                show_error_in_console(f"Neither directory nor file: {selected}", fm)
                return

        def select_with_fzf(fzf_cmd, input, fm):
            fm.ui.suspend()
            try:
                # stderr is used to open to attach to /dev/tty
                proc = subprocess.Popen(fzf_cmd, stdout=subprocess.PIPE, stdin=subprocess.PIPE, text=True)
                stdout, _ = proc.communicate(input=input)

                # ESC gives 130
                if proc.returncode not in [0, 130]:
                    raise Exception(f"Bad process exit code: {proc.returncode}, stdout={stdout}")
            finally:
                fm.ui.initialize()
            return stdout.strip()

class dir_history_navigate(Command):
    def execute(self):
        lst = []
        for d in reversed(self.fm.tabs[self.fm.current_tab].history.history):
            lst.append(d.path)

        fm = self.fm
        selected = select_with_fzf(["fzf"], "\n".join(lst), fm)

        navigate_path(fm, selected)