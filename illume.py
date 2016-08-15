from cue_sdk import *
from time import sleep
import threading, os, sys
import tkinter as tk
from ctypes import Structure, windll, c_uint, sizeof, byref
from ctypes import CFUNCTYPE, POINTER, c_int, c_void_p, wintypes
import atexit

if len(sys.argv) > 1:
    slt = int(sys.argv[1])
    sleep(slt)

Corsair = CUESDK("./CUESDK_2013.dll")
intr = True

khook_id = 0
mhook_id = 0
intr = True
handlers = []

def listen():

	def kbll_handler(nCode, wParam, lParam):
		"""
		Processes a low level Windows keyboard event.
		"""
		for handler in handlers:
			handler()

		return windll.user32.CallNextHookEx(khook_id, nCode, wParam, lParam)

	def mll_handler(nCode, wParam, lParam):
		"""
		Processes a low level Windows Mouse event.
		"""
		for handler in handlers:
			handler()

		return windll.user32.CallNextHookEx(mhook_id, nCode, wParam, lParam)

	# Our low level handler signature.
	CMPFUNC = CFUNCTYPE(c_int, c_int, c_int, POINTER(c_void_p))
	# Convert the Python handler into C pointer.
	kbpointer = CMPFUNC(kbll_handler)
	mpointer = CMPFUNC(mll_handler)

	global intr, khook_id, mhook_id

	khook_id = windll.user32.SetWindowsHookExA(13, kbpointer, windll.kernel32.GetModuleHandleA(None), 0)
	mhook_id = windll.user32.SetWindowsHookExA(14, mpointer, windll.kernel32.GetModuleHandleA(None), 0)
	# Register to remove the hook when the interpreter exits.
	atexit.register(windll.user32.UnhookWindowsHookEx, khook_id)
	atexit.register(windll.user32.UnhookWindowsHookEx, mhook_id)

	message = wintypes.MSG()
	while intr:
		msg = windll.user32.GetMessageW(byref(message), 0, 0, 0)
		if msg == -1:
			unhook_all()
			break
		windll.user32.TranslateMessage(byref(message))
		windll.user32.DispatchMessageW(byref(message))


def unhook_all():
	global intr, khook_id, mhook_id
	windll.user32.UnhookWindowsHookEx(khook_id)
	windll.user32.UnhookWindowsHookEx(mhook_id)
	print("Hook ended")

class LASTINPUTINFO(Structure):
    _fields_ = [
        ('cbSize', c_uint),
        ('dwTime', c_uint),
    ]

def get_duration():
    lastInputInfo = LASTINPUTINFO()
    lastInputInfo.cbSize = sizeof(lastInputInfo)
    windll.user32.GetLastInputInfo(byref(lastInputInfo))
    millis = windll.kernel32.GetTickCount() - lastInputInfo.dwTime
    return millis / 1000.0

class Checker(threading.Thread):
    idleTime = 300
    global intr
    def __init__(self):
        super(Checker, self).__init__()
        self.setIdleTime(5)
    def run(self):
        while intr:
            sleep(5)
            tillIdle = get_duration()
            #print("Current IdleTime: %d" % tillIdle)
            if (tillIdle >= self.idleTime):
                Corsair.RequestControl(CAM.ExclusiveLightingControl)
    def setIdleTime(self, val):
        print("Set idletime: %d" % val)
        self.idleTime = val*60

class Hook(threading.Thread):
    def __init__(self):
        super(Hook, self).__init__()

    def run(self):
        handlers.append(self.OnAnyEvent)
        listen()

    def OnAnyEvent(self):
        Corsair.ReleaseControl(CAM.ExclusiveLightingControl)
        return True

class App(tk.Tk):

    def __init__(self, val="0"):
        self.checker = Checker()
        self.checker.start()

        self.hook = Hook()
        self.hook.start()

        if val=="0":
            tk.Tk.__init__(self)
            self.label1 = tk.Label(self, text="Idle Time:").grid(row=0, column=0)
            self.entry = tk.Entry(self, bd=5)
            self.entry.insert(0, '5')
            self.entry.grid(row=0, column=1)
            self.label2 = tk.Label(self, text="min").grid(row=0, column=2)
            self.btn = tk.Button(self, text="SET", command=self.setIdleTime).grid(row=1, column=0, columnspan=3)
            #self.min = tk.Button(self, text="Minimize", command=self.Minimize).grid(row=1, column=2, columnspan=2)
            self.cr = tk.Label(self, text="Created by Nafis").grid(row=3, columnspan=3)
        else:
            self.checker.setIdleTime(int(val))

    def setIdleTime(self):
        s = self.entry.get()
        print("New Value: %s" % s)
        f = open('idletime', 'w')
        f.write(s)
        f.close()
        self.checker.setIdleTime(int(s))

if __name__ == "__main__":
    cur_pid = os.getpid()

    if os.path.exists('pid'):
        pidf = open('pid', 'r')
        prev_pid = pidf.readline()
        os.system("taskkill /pid " + prev_pid + " /f")
        pidf.close()

    npidf = open('pid', 'w')
    npidf.write(str(cur_pid))
    npidf.close()

    if(len(sys.argv) == 1):

        cdir = os.getcwd()
        cdir = 'cd /d "' + cdir + '"\n'
        strt = 'start "illume" illume.exe 30\n'
        f = open('start_illume.bat', 'w')
        f.write(cdir)
        f.write(strt)
        f.write("exit")
        f.close()

        app = App()
        app.wm_title("Illume")
        app.mainloop()
    else:
        if os.path.exists('idletime'):
            f = open('idletime', 'r')
            val = f.readline()
            f.close()
        else:
            val = "5"
        app = App(val)
    #intr = False
    #unhook_all()
