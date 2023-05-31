def select_dir():
    import tkinter as tk
    from tkinter import filedialog


    root = tk.Tk()
    root.withdraw()
    dir1 = filedialog.askdirectory()

    return dir1
