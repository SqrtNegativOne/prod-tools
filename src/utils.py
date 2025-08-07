import tkinter

def notif(title, message, logger):
    logger.info(f"Notification: {title} - {message}")
    # toaster = WindowsToaster('Brave Blocker')
    # newToast = Toast()
    # newToast.text_fields = [title, message]
    # toaster.show_toast(newToast)

    # Show a tkinter window with the notice for 2 seconds
    root = tkinter.Tk()
    root.title(title)
    root.geometry("350x100")
    root.config(bg='black')
    root.attributes("-topmost", True)
    root.resizable(False, False)
    label = tkinter.Label(root, text=message, font=("Segoe UI", 16), wraplength=320, justify="center", foreground='white')
    label.pack(expand=True, fill="both", padx=10, pady=10)
    root.after(800, root.destroy)
    root.mainloop()
