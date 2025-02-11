from ModIO import PspRamIO
from struct import pack, unpack
from time import sleep
from json import dump, load
import win32api
from win32gui import GetWindowText, GetForegroundWindow
from tkinter import *
from tkinter.ttk import *


CAMERA_YAW      = 0x08C316E4
CAMERA_PITCH    = 0x08C336B0

H_SENSITIVITY   = 0.008
V_SENSITIVITY   = 0.01
H_CAP           = 1
V_CAP           = .4
H_SMOOTH_FACTOR = .5
V_SMOOTH_FACTOR = 2


class CameraInterface:
    def __init__(self, psp_ram):
        self.ram = psp_ram
    
    @property
    def yaw(self):
        self.ram.seek(CAMERA_YAW)
        return unpack("f", self.ram.read(4))[0]

    @yaw.setter
    def yaw(self, yaw):
        self.ram.seek(CAMERA_YAW)
        self.ram.write(pack("f", yaw))
    
    @property
    def pitch(self):
        self.ram.seek(CAMERA_PITCH)
        return unpack("f", self.ram.read(4))[0]
    
    @pitch.setter
    def pitch(self, pitch):
        self.ram.seek(CAMERA_PITCH)
        self.ram.write(pack("f", pitch))


class App(Tk):
    def __init__(self):
        super().__init__()
        self.running = False
        self.working = False
        self.title("ACLR - Mouse Camera")
        self.iconbitmap("icon.ico")
        self.vars = {
            "H_SENSITIVITY"   : H_SENSITIVITY,
            "V_SENSITIVITY"   : V_SENSITIVITY,
            "H_CAP"           : H_CAP,
            "V_CAP"           : V_CAP,
            "H_SMOOTH_FACTOR" : H_SMOOTH_FACTOR,
            "V_SMOOTH_FACTOR" : V_SMOOTH_FACTOR,
        }

        self.load_settings()

        self.hsens = DoubleVar()
        self.hsens.set(self.vars["H_SENSITIVITY"]*10)
        self.vsens = DoubleVar()
        self.vsens.set(self.vars["V_SENSITIVITY"]*10)
        self.hcap = DoubleVar()
        self.hcap.set(self.vars["H_CAP"])
        self.vcap = DoubleVar()
        self.vcap.set(self.vars["V_CAP"])
        self.hsfac = DoubleVar()
        self.hsfac.set(self.vars["H_SMOOTH_FACTOR"])
        self.vsfac = DoubleVar()
        self.vsfac.set(self.vars["V_SMOOTH_FACTOR"])
        
        Label(self, text="H Sensitivity").pack()
        Scale(self, variable=self.hsens, from_=0, to=3).pack()
        Label(self, text="V Sensitivity").pack()
        Scale(self, variable=self.vsens, from_=0, to=3).pack()
        Label(self, text="H Cap").pack()
        Scale(self, variable=self.hcap, from_=0, to=10).pack()
        Label(self, text="V Cap").pack()
        Scale(self, variable=self.vcap, from_=0, to=10).pack()
        Label(self, text="H Smooth Factor").pack()
        Scale(self, variable=self.hsfac, from_=0, to=1).pack()
        Label(self, text="V Smooth Factor").pack()
        Scale(self, variable=self.vsfac, from_=0, to=1).pack()
        Button(self, text="Start", command=self.start).pack()
        Button(self, text="Stop", command=self.stop).pack()
    
    def load_settings(self) -> None:
        try:
            with open("config.json", "r", encoding="utf-8") as file:
                self.vars.update(load(file))
        except FileNotFoundError:
            pass

    def save_settings(self) -> None:
        with open("config.json", "w", encoding="utf-8") as file:
            dump(self.vars, file)

    def destroy(self):
        self.save_settings()
        self.running = False
        return super().destroy()

    def update(self):
        self.vars = self.vars = {
            "H_SENSITIVITY"   : self.hsens.get()/10,
            "V_SENSITIVITY"   : self.vsens.get()/10,
            "H_CAP"           : self.hcap.get(),
            "V_CAP"           : self.vcap.get(),
            "H_SMOOTH_FACTOR" : self.hsfac.get(),
            "V_SMOOTH_FACTOR" : self.vsfac.get(),
        }
        return super().update()

    def start(self) -> None:
        self.working = True
    
    def stop(self) -> None:
        self.working = False
    
    def run(self) -> None:
        self.update()
        self.running = True

        CENTER = (win32api.GetSystemMetrics(0) // 2, win32api.GetSystemMetrics(1) // 2)  # Get center of the screen coords
        win32api.SetCursorPos(CENTER)
        
        sensitivity = [self.vars["H_SENSITIVITY"], self.vars["V_SENSITIVITY"]]

        pitch = 0
        yaw = 0
        last_yaw = 0

        psp_ram = PspRamIO()  # hook to ppsspp memory
        cam = CameraInterface(psp_ram)

        while self.running:
            window_title = GetWindowText(GetForegroundWindow())

            self.update()

            if not self.working:
                sleep(1/60)
                continue

            if "PPSSPP" not in window_title:
                sleep(1/60)
                continue
            if "NPUH10024" not in window_title:
                sleep(1/60)
                continue
            
            curr_pos = win32api.GetCursorPos()
            win32api.SetCursorPos(CENTER)

            movement = (
                min(self.vars["H_CAP"], max(-self.vars["H_CAP"], (curr_pos[0] - CENTER[0]) * sensitivity[0])),
                min(self.vars["V_CAP"], max(-self.vars["V_CAP"], (curr_pos[1] - CENTER[1]) * sensitivity[1]))
            )

            pitch = pitch - movement[1]
            pitch = (cam.pitch * self.vars["V_SMOOTH_FACTOR"] + pitch) / (1 + self.vars["V_SMOOTH_FACTOR"])
            pitch = max(-1.2, min(1.2, pitch))
            
            yaw = yaw + movement[0]
            yaw = (last_yaw * self.vars["H_SMOOTH_FACTOR"] + yaw) / (1 + self.vars["H_SMOOTH_FACTOR"])
            if yaw < 0:
                yaw += 6.28319
            elif yaw > 6.28319:
                yaw -= 6.28319
            last_yaw = yaw
            
            cam.yaw, cam.pitch = yaw, pitch
            
            sleep(1/60)


if __name__ == "__main__":
    app = App()
    app.run()
