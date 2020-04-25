# -*- coding: utf-8 -*-
import os
import sys
import time
import threading
import json
import getpass
import concurrent.futures
import winreg as reg
from PyQt5 import uic
import requests
from requests import get, post
from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow


class MyWidget(QMainWindow):
    USER_NAME = getpass.getuser()

    dict_mini_phrases = {
        'user_not_found': 'Пользователь не найден.',
        'key_active': 'Ключ уже активирован!',
        'add_program': 'Ключ успешно добавлен!',
        'exit_program': 'Вы успешно отвязали ключ от приложения',
        'error_server': 'Ошибка сервера! Убедитесь, что вы подключены к сети!',
        'not_key_user': 'Вы не ввели ключ!',
        'not_found_key_user': 'Неверный ключ!',
        'program_not_activated': 'Активируйте программу, чтобы начать пользоваться сервисом.',
        'program_activated': 'Программа активированна',
        'key_not_active': 'Ключ уже не активен.',
        'not_key_user_exit': 'Чтобы открепить приложение от сервера, введите ключ.',
        'exit_program_success': 'Программа успешно отключена от сервера'
    }

    def __init__(self):
        super().__init__()
        uic.loadUi('interface/interface.ui', self)
        # Можно ли выйти из программы или нет
        self.output_program = False
        self.key_user = ''
        self.start_check = None
        # Активирован ключ или нет
        self.key_active = False
        self.open_save_file()
        # path_program = os.path.abspath(os.curdir) + r'\program.exe'
        # print(self.USER_NAME)
        # print(path_program)
        # print(type(path_program))
        # self.add_to_startup(path_program)
        self.button_add_key.clicked.connect(self.button_input)

        self.dict_functions_pc = {
            'shutdown': self.shutdown_pc,
            'reboot': self.reboot_pc,
            'sleep_mode': self.sleep_mode_pc
        }
        if self.key_active:
            self.start_check_server()

    # Данный метод запускает проверку, которая отправляет запросы на сервер
    def start_check_server(self):
        self.start_check = threading.Thread(target=self.check_commands_pc, name='Check Command PC', args=(), daemon=True)
        self.start_check.start()

    # Нажатие на кнопку
    def button_input(self):
        print(self.key_active)
        if self.key_active is False:
            self.active_key()
        else:
            self.exit_program()

    # Выход из программы
    def exit_program(self):
        key = self.input_key.text()
        if key == "":
            self.add_history(self.dict_mini_phrases['not_key_user_exit'])
        else:
            if self.exit_program_bd(key) is not False:
                self.input_key.setText('')
                self.button_add_key.setText('Войти')
                with open('save_key.txt', 'w') as file:
                    file_write = file.write('')

    # Открывает файл с ключом
    def open_save_file(self):
        with open('save_key.txt', 'r') as file:
            file_read = file.readline()
            self.input_key.setText(file_read)
            if file_read == "":
                self.key_active = False
                self.add_history(self.dict_mini_phrases['program_not_activated'])
                self.button_add_key.setText('Войти')
            else:
                self.key_active = True
                self.key_user = self.input_key.text()
                self.add_history(self.dict_mini_phrases['program_activated'])
                self.button_add_key.setText('Выйти')

    # Активирует ключ
    def active_key(self):
        key = self.input_key.text()
        if key == "":
            self.add_history(self.dict_mini_phrases['not_key_user'])
        else:
            if self.check_user_key(key) is not False:
                self.add_history(self.dict_mini_phrases['add_program'])
                self.input_key.setText(key)
                self.button_add_key.setText('Выйти')
                self.key_active = True
                self.key_user = key
                self.start_check_server()
                with open('save_key.txt', 'w') as file:
                    file_write = file.write(key)

    # Данный метод отключает программу от сервера
    def exit_program_bd(self, key):
        information_json = {'key_user': key}
        with concurrent.futures.ThreadPoolExecutor() as executor:
            request_server = executor.submit(self.request_server, 'exit_key_program', information_json)
            value = request_server.result()
            #  print(value)
            if value == 'error_server':
                self.add_history(self.dict_mini_phrases['error_server'])
            result = json.loads(value.text)
            #  print(result)
            if 'error' in result:
                self.add_history(self.dict_mini_phrases[result['error']])
                return False
            else:
                self.key_active = False
                self.add_history(self.dict_mini_phrases[result['success']])
                return True

    def add_history(self, text):
        self.history.addItem(text)

    # Проверка ключа, чтобы убедиться, что пользователь с таким ключом существует
    def check_user_key(self, key):
        information_json = {'key_user': key}
        with concurrent.futures.ThreadPoolExecutor() as executor:
            request_server = executor.submit(self.request_server, 'add_key_program', information_json)
            value = request_server.result()
            if value == 'error_server':
                self.add_history(self.dict_mini_phrases['error_server'])
                return False
            result = json.loads(value.text)
            if 'error' in result:
                self.add_history(self.dict_mini_phrases[result['error']])
                return False
            elif 'key_user' in result:
                return result['key_user']

    # Данный метод проверяет все команды, которые приходят на сервер
    def check_commands_pc(self):
        while True:
            if not self.key_active:
                print('exit check_command')
                break
            key = self.key_user
            information_json = {'key_user': key}
            with concurrent.futures.ThreadPoolExecutor() as executor:
                request_server = executor.submit(self.request_server, 'get_all_functions_client', information_json)
                value = request_server.result()
                if value == 'error_server':
                    self.add_history(self.dict_mini_phrases['error_server'])
                    return False
                result = json.loads(value.text)
                if 'error' not in result:
                    path_program_select = result['path_program_select']
                    self.start_program(path_program_select)
                    path_program_select = result['scenario_select']
                    self.start_scenario(path_program_select)
                    if result['select_pc_function'] is not None:
                        self.dict_functions_pc.get(result['select_pc_function'])()
                    print(result['path_program_select'], result['scenario_select'], result['select_pc_function'])
            time.sleep(2)

    # Даннный скрипт создает файл, который запускает данную программу при старте windows
    # def add_to_startup(self, file_path=""):
    #     key = 'HKEY_CURRENT_USER'
    #     key_value = "Software\Microsoft\Windows\CurrentVersion\Run"
    #     open = reg.OpenKey(key, key_value, 0, reg.KEY_ALL_ACCESS)
    #     reg.SetValueEx(open, "any_name", 0, reg.REG_SZ, file_path)
    #     reg.CloseKey(open)

    # Запускает программу, которую отправил сервер
    def start_program(self, path_program):
        if path_program is not None:
            try:
                os.startfile(path_program)
            except FileNotFoundError:
                self.add_history(f'Данный путь не найден: {path_program}')

    # Запускает сценарий, который отправил сервер
    def start_scenario(self, programs):
        if programs is not None:
            for path_program in programs:
                self.start_program(path_program)

    # Данный метод выключает ПК
    def shutdown_pc(self):
        print('Выкл ПК')
        os.system("shutdown /s /t 1")

    # Данный метод перезагружает ПК
    def reboot_pc(self):
        print("Перезагрузка ПК")
        os.system("shutdown /r /t 1")

    # Данный метод создает переход в спящий режим
    def sleep_mode_pc(self):
        print("Вход в спящий режим")
        os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")

    # Отправляет запрос на сервер и возвращает ответ
    def request_server(self, place, information_json):
        while True:
            try:
                request = post(f'https://website-computer-manager.herokuapp.com/{place}', json=information_json)
                if request.status_code != 200:
                    print("Ошибка. Код ответа: %s", request.status)
                    time.sleep(1)
                    continue
                return request
            except requests.RequestException:
                return 'error_server'


app = QApplication(sys.argv)
ex = MyWidget()
#  ex.add_to_startup()
ex.show()
sys.exit(app.exec_())
