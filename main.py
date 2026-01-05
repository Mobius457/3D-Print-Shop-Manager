import ttkbootstrap as ttk
from src.ui.app import FilamentManagerApp

if __name__ == "__main__":
    app = ttk.Window(themename="flatly")
    FilamentManagerApp(app)
    app.mainloop()
