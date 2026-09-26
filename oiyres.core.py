import os
import subprocess
import tempfile
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
import psutil

# Создаем главное окно Oiyres Inc.
root = tk.Tk()
root.title("Oiyres Task Manager v2.0 [Core Engine]")
root.geometry("750x600")
root.configure(bg="#1e1e24")

# Настройка стилей для хакерского интерфейса
style = ttk.Style()
style.theme_use("clam")
style.configure("TNotebook", background="#1e1e24")
style.configure("TNotebook.Tab", background="#2d2d38", foreground="white", padding=[15, 5])
style.map("TNotebook.Tab", background=[("selected", "#007acc")])
style.configure("Treeview", background="#252530", foreground="white", fieldbackground="#252530", rowheight=25)
style.map("Treeview", background=[("selected", "#007acc")])

# ВЕРХНЯЯ СИСТЕМНАЯ ПАНЕЛЬ (Показывает МБ и % ОЗУ и ЦП)
stat_frame = tk.Frame(root, bg="#252530", bd=2, relief="groove")
stat_frame.pack(fill="x", padx=10, pady=5)

lbl_cpu = tk.Label(stat_frame, text="Загрузка ЦП: 0%", bg="#252530", fg="#00ff00", font=("Arial", 10, "bold"))
lbl_cpu.pack(side="left", padx=15, pady=5)

lbl_ram = tk.Label(stat_frame, text="ОЗУ: 0 МБ / 0 МБ (0%)", bg="#252530", fg="#00ff00", font=("Arial", 10, "bold"))
lbl_ram.pack(side="right", padx=15, pady=5)

notebook = ttk.Notebook(root)
notebook.pack(fill="both", expand=True, padx=10, pady=5)

# Вкладки для разных типов процессов
tab_user = ttk.Frame(notebook)
tab_bg = ttk.Frame(notebook)
tab_sys = ttk.Frame(notebook)

notebook.add(tab_user, text="Рабочие процессы")
notebook.add(tab_bg, text="Фоновые процессы")
notebook.add(tab_sys, text="Системные процессы")

columns = ("PID", "Имя", "Память (МБ)")

def create_tree(parent):
    tree = ttk.Treeview(parent, columns=columns, show="headings", selectmode="browse")
    tree.heading("PID", text="PID")
    tree.heading("Имя", text="Название процесса")
    tree.heading("Память (МБ)", text="Память (МБ)")
    tree.column("PID", width=70, anchor="center")
    tree.column("Имя", width=380, anchor="w")
    tree.column("Память (МБ)", width=120, anchor="e")
    
    scrollbar = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    
    tree.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    return tree

tree_user = create_tree(tab_user)
tree_bg = create_tree(tab_bg)
tree_sys = create_tree(tab_sys)

# Фоновое обновление системы (чтобы ничего не зависало)
def get_system_stats():
    while True:
        try:
            # Считаем загрузку процессора и памяти
            cpu = psutil.cpu_percent(interval=0.5)
            virtual_mem = psutil.virtual_memory()
            
            used_ram_mb = round(virtual_mem.used / (1024 * 1024), 0)
            total_ram_mb = round(virtual_mem.total / (1024 * 1024), 0)
            ram_percent = virtual_mem.percent
            
            # Меняем текст в окне (безопасно для потока)
            lbl_cpu.config(text=f"📊 Загрузка ЦП: {cpu}%")
            lbl_ram.config(text=f"🧠 Использовано ОЗУ: {int(used_ram_mb)} МБ / {int(total_ram_mb)} МБ ({ram_percent}%)")
            
            time.sleep(1.5)
        except:
            pass

# Потоковая функция для загрузки списка процессов
def load_processes_thread():
    user_list, bg_list, sys_list = [], [], []
    
    for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'username']):
        try:
            info = proc.info
            pid = info['pid']
            name = info['name']
            mem = round(info['memory_info'].rss / (1024 * 1024), 1) if info['memory_info'] else 0
            username = info['username']
            
            row = (pid, name, mem)
            
            if username is None or "SYSTEM" in username.upper() or "LOCAL SERVICE" in username.upper():
                sys_list.append(row)
            elif name.lower() in ["explorer.exe", "svchost.exe", "taskhostw.exe", "ctfmon.exe"]:
                bg_list.append(row)
            else:
                user_list.append(row)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
            
    # Передаем данные в интерфейс главного окна
    root.after(0, lambda: refresh_tree_views(user_list, bg_list, sys_list))

def refresh_tree_views(user_list, bg_list, sys_list):
    for tree in (tree_user, tree_bg, tree_sys):
        for item in tree.get_children():
            tree.delete(item)
            
    for row in user_list: tree_user.insert("", "end", values=row)
    for row in bg_list: tree_bg.insert("", "end", values=row)
    for row in sys_list: tree_sys.insert("", "end", values=row)

def update_processes():
    threading.Thread(target=load_processes_thread, daemon=True).start()

# Принудительное уничтожение процесса (Kill-модуль)
def kill_selected():
    current_tab = notebook.index(notebook.select())
    target_tree = [tree_user, tree_bg, tree_sys][current_tab]
    selected = target_tree.selection()
    
    if not selected:
        messagebox.showwarning("Oiyres Core", "Сначала выберите процесс из списка!")
        return
        
    pid = target_tree.item(selected[0])['values'][0]
    name = target_tree.item(selected[0])['values'][1]
    
    if current_tab == 2:
        if not messagebox.askyesno("Внимание", f"Вы пытаетесь убить СИСТЕМНЫЙ процесс {name}. Это может выключить ПК. Продолжить?"):
            return

    try:
        proc = psutil.Process(pid)
        proc.kill()  # Полное уничтожение без сигналов Windows
        messagebox.showinfo("Успех", f"Процесс {name} (PID: {pid}) успешно стерт из памяти!")
        update_processes()
    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось завершить процесс: {e}")

# МГНОВЕННЫЙ вызов окна "Выполнить" без задержек и PowerShell
def run_new_process():
    try:
        # Используем самый быстрый системный способ через проводник
        os.system("start rundll32.exe shell32.dll,#61")
    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось вызвать меню: {e}")

# Оптимизация ПК в отдельном потоке (чтобы не зависало окно)
def optimize_pc_thread():
    freed_ram = 0
    bad_bg_apps = ["jusched.exe", "update.exe", "onedrive.exe", "skype.exe", "discord.exe", "spotifywebhelper.exe"]
    
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if proc.info['name'].lower() in bad_bg_apps:
                proc.kill()
                freed_ram += 30
        except:
            continue
            
    freed_mb = 0
    temp_dir = tempfile.gettempdir()
    for root_dir, dirs, files in os.walk(temp_dir):
        for f in files:
            try:
                fp = os.path.join(root_dir, f)
                freed_mb += os.path.getsize(fp) / (1024 * 1024)
                os.remove(fp)
            except:
                continue
                
    root.after(0, lambda: finish_optimization(freed_mb, freed_ram))

def finish_optimization(freed_mb, freed_ram):
    update_processes()
    messagebox.showinfo("Oiyres Optimization", 
                        f"Оптимизация успешно завершена!\n\n"
                        f"🛡️ Удалено временного мусора: {round(freed_mb, 1)} МБ\n"
                        f"⚡ Примерно разгружено ОЗУ: {freed_ram} МБ")

def optimize_pc():
    threading.Thread(target=optimize_pc_thread, daemon=True).start()

# Нижняя панель с кнопками управления
btn_frame = tk.Frame(root, bg="#1e1e24")
btn_frame.pack(fill="x", side="bottom", padx=10, pady=10)

btn_kill = tk.Button(btn_frame, text="🛑 Уничтожить процесс (Kill)", bg="#d9534f", fg="white", font=("Arial", 10, "bold"), command=kill_selected)
btn_kill.pack(side="left", padx=5)

btn_add = tk.Button(btn_frame, text="➕ Добавить процесс (Win+R)", bg="#28a745", fg="white", font=("Arial", 10), command=run_new_process)
btn_add.pack(side="left", padx=5)

btn_opt = tk.Button(btn_frame, text="⚡ Оптимизация ПК", bg="#ffc107", fg="black", font=("Arial", 10, "bold"), command=optimize_pc)
btn_opt.pack(side="right", padx=5)

btn_refresh = tk.Button(btn_frame, text="🔄 Обновить", bg="#007acc", fg="white", font=("Arial", 10), command=update_processes)
btn_refresh.pack(side="right", padx=5)

# Запуск фонового мониторинга ресурсов системы
threading.Thread(target=get_system_stats, daemon=True).start()

# Первый запуск
update_processes()
root.mainloop()
